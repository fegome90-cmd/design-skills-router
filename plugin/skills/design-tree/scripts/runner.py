"""Portable, supervised ledger for the unchanged v0.4 design tree.

No network, installers or project-code execution. Receipts are operator-supplied
records, NOT authenticated human identities. Hashes detect accidental drift;
an agent able to rewrite this package/state can bypass these checks.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
import sqlite3
import os
import re
import sys
sys.dont_write_bytecode = True
import tempfile
from functools import wraps
from datetime import datetime, timezone
from pathlib import Path
from tree_model import expand_model, flatten

SKILL_DIR = Path(__file__).resolve().parents[1]
BASE = SKILL_DIR / 'references' / 'tree-v0.4'
SCHEMA = 'design-tree-ledger/0.3'
LEGACY_SCHEMA = 'design-tree-ledger/0.1'
from contracts import evaluate_contracts, validate_contracts, policy_hash
from verification import validate_results, evaluate_results
from assistance import validate_assistance, assistance_action
import node_context

class GateError(ValueError):
    """An explicit gate failure; no requested mutation has been committed."""


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def now():
    return datetime.now(timezone.utc).isoformat()


def require(condition, code):
    if not condition:
        raise GateError(code)


def nonblank(value):
    return isinstance(value, str) and bool(value.strip())


def file_hash(path):
    p = Path(path)
    require(p.is_file() and not p.is_symlink(), 'FILE_MISSING_OR_SYMLINK')
    require(p.stat().st_size <= 16 * 1024 * 1024, 'FILE_TOO_LARGE')
    return hashlib.sha256(p.read_bytes()).hexdigest()


def human_receipt(receipt, target_hash, kind):
    require(isinstance(receipt, dict) and receipt.get('role') == 'user', 'HUMAN_RECEIPT_REQUIRED')
    require(receipt.get('kind') == kind, 'RECEIPT_SCOPE_MISMATCH')
    require(receipt.get('target_hash') == target_hash, 'RECEIPT_HASH_MISMATCH')
    require(all(nonblank(receipt.get(k)) for k in ('message_ref', 'quote')), 'HUMAN_MESSAGE_REFERENCE_REQUIRED')
    # This is a protocol check, not authentication of the cited message.
    return {**copy.deepcopy(receipt), 'recorded_at': now(), 'authentication': 'OPERATOR_ASSERTED_NOT_AUTHENTICATED'}


def read_snapshot(fn):
    """Memoize repeated validations within ONE synchronous read operation only.

    No cache survives a public read, and no mutator is decorated. This is not
    persisted authority: next calls re-open and revalidate their evidence.
    """
    @wraps(fn)
    def wrapped(self, state, *args):
        outer = getattr(self, '_read_cache', None) is None
        if outer:
            self._read_cache = {}
        key = (fn.__name__, id(state), args)
        try:
            if key not in self._read_cache:
                self._read_cache[key] = fn(self, state, *args)
            return self._read_cache[key]
        finally:
            if outer:
                self._read_cache = None
    return wrapped


class Router:
    def __init__(self, package_root=None):
        self.skill_dir = Path(package_root)/"skills/design-tree" if package_root else SKILL_DIR
        self.base = self.skill_dir/"references/tree-v0.4"
        self.tree = json.loads((self.base/'tree.json').read_text())
        self.rules = json.loads((self.base/'rules.json').read_text())
        inv = json.loads((self.base/'skill-inventory.json').read_text())
        self.inventory = {r['id']: r for r in inv['skills']}
        self.tree_hash = hashlib.sha256((self.base/'tree.json').read_bytes()).hexdigest()
        self.inventory_hash = hashlib.sha256((self.base/'skill-inventory.json').read_bytes()).hexdigest()
        self.verify_baseline()
        self.expanded = expand_model(self.tree)
        self.nodes = {n['id']: n for n in flatten(self.expanded['root'])}
        self.parents = {}
        for n in self.nodes.values():
            for edge in n['children']:
                self.parents[edge['node']['id']] = n['id']
        cp=self.skill_dir/'references/contracts.json'
        self.contracts=json.loads(cp.read_text())
        require(not validate_contracts(self.contracts,self.nodes,self.inventory),'CONTRACTS_INVALID')
        require(self.contracts.get('baseline',{}).get('tree_hash')==self.tree_hash,'CONTRACT_BASELINE_MISMATCH')

    def verify_baseline(self):
        lock=json.loads((self.skill_dir/'references'/'baseline-lock.json').read_text())
        for name, expected in lock.items():
            require(file_hash(self.base/name) == expected, 'BASELINE_FILE_DRIFT:'+name)
        return True

    def new_state(self, project_id, medium, mode, scope, *, context_pilot=False):
        require(nonblank(project_id) and nonblank(scope), 'PROJECT_AND_SCOPE_REQUIRED')
        require(medium == 'web', 'PILOT_SUPPORTS_WEB_ONLY')
        require(mode in ('design', 'audit'), 'INVALID_MODE')
        require(not context_pilot or mode == 'audit', 'CONTEXT_PILOT_REQUIRES_AUDIT')
        state = {'schema': SCHEMA, 'project_id': project_id, 'medium': medium,
                'mode': mode, 'scope': scope, 'revision': 0,
                'tree_hash': self.tree_hash, 'inventory_hash': self.inventory_hash,
                'structures': {}, 'records': {}, 'sources': {}, 'candidates': {},
                'inventory_proposal': None, 'inventory_confirmation': None,
                'history': [], 'created_at': now(), 'facts':{}, 'structure_sets':{},
                'assistance_level':'manual','grants':{},'active_grant_id':None,
                'phase_map':None,'phase_map_hash':None,'phase_map_receipt':None,
                'phases':{},'active_phase_id':None}
        if context_pilot:
            state['context_profile'] = node_context.PROFILE
            state['context_packets'] = {}
        return state

    def check_state(self, state):
        require(state.get('schema') == SCHEMA, 'STATE_SCHEMA_MISMATCH')
        require(state.get('tree_hash') == self.tree_hash and state.get('inventory_hash') == self.inventory_hash, 'BASELINE_MISMATCH')
        require(state.get('medium') == 'web', 'PILOT_SUPPORTS_WEB_ONLY')
        require(state.get('mode') in ('design', 'audit'), 'INVALID_MODE')
        self.verify_baseline()
        if state.get('phase_map'):
            require(digest(state['phase_map'])==state.get('phase_map_hash'),'PHASE_MAP_CHANGED')
            human_receipt(state.get('phase_map_receipt'),state['phase_map_hash'],'phase_map')
            for p in state['phase_map']['phases']:
                actual=state.get('phases',{}).get(p['id'],{})
                require(all(actual.get(k)==v for k,v in p.items()),'PHASE_DEFINITION_CHANGED')

    def node(self, node_id):
        require(node_id in self.nodes, 'UNKNOWN_NODE:'+str(node_id))
        return self.nodes[node_id]

    def structure_hash(self, node_id):
        n=self.node(node_id)
        return digest({'baseline':self.tree_hash, 'id':node_id, 'definition':n['definition_id'],
                       'title':n['title'], 'kind':n['kind'], 'rules':n.get('rule_ids',[]),
                       'alternatives':[(c['answer'],c['node']['id']) for c in n['children']]})

    @read_snapshot
    def active(self, state):
        self.check_state(state)
        out=[]
        def walk(n):
            out.append(n['id'])
            rec=state['records'].get(n['id'],{})
            if not self.record_current(state,n['id']):return
            if n['kind']=='decision':
                for e in n['children']:
                    if e['node']['id']==rec['proposal']['selected']:walk(e['node'])
            elif n['kind']=='all':
                for e in n['children']:walk(e['node'])
        walk(self.expanded['root'])
        return out

    @read_snapshot
    def frontier(self,state):
        return [nid for nid in self.active(state) if not self.record_current(state,nid)]

    def skills_for(self,node_id):
        n=self.node(node_id)
        ids=set(n.get('skills',[]))
        for rid in n.get('rule_ids',[]):
            s=self.rules[rid].get('skill')
            if s in self.inventory:ids.add(s)
        return sorted(ids)

    @read_snapshot
    def packet(self,state,node_id):
        self.check_state(state)
        n=self.node(node_id)
        project_status = state['records'].get(node_id, {}).get('status', 'PENDING')
        if self.decision_awaiting_human(state, node_id):
            project_status = 'AWAITING_HUMAN'
        return {'node_id':node_id, 'definition_id':n['definition_id'], 'title':n['title'],
                'kind':n['kind'], 'active':node_id in self.active(state),
                'structure_hash':self.structure_hash(node_id),
                'structure_status':state['structures'].get(node_id,{}).get('status','PENDING'),
                'project_status':project_status,
                'criterion':n.get('criterion',''), 'output':n.get('output',''),
                'requires':n.get('requires',[]), 'context_mode':n.get('context_mode'),
                'write_policy':n.get('write_policy'), 'candidate_key':n.get('candidate_key'),
                'terminal_status':n.get('terminal_status'), 'proposal_status':n.get('proposal_status'),
                'alternatives':[{'answer':c['answer'],'node_id':c['node']['id'],
                                 'title':c['node']['title']} for c in n['children']],
                'skills':[{'id':i,'name':self.inventory[i]['name'],
                           'url':self.inventory[i]['source_url'],
                           'commit':self.inventory[i]['candidate_commit'],
                           'source_receipt':state['sources'].get(i)} for i in self.skills_for(node_id)],
                'criteria':[self.rules[r] for r in n.get('rule_ids',[])],
                'candidate_contract':n.get('adoption_contract'),
                'phase_id':self.phase_for(state,node_id),'assistance':self.decision_delegation(state,node_id),
                'policy_hash':policy_hash(n,self.rules,self.contracts),'context_hash':self.context_hash(state,node_id),
                'relationships':evaluate_contracts(n,{'facts':state.get('facts',{}),'operation':'reference'},self.contracts),
                'notice':'Inspecting a packet is not consulting its external sources or approving anything.'}

    def blocked(self,node_id):
        n=self.node(node_id)
        return any(str(n.get(k,'')).startswith('BLOCKED') for k in ('terminal_status','proposal_status'))

    def _bounded_prerequisite_node(self,state,phase,node_id):
        if (state.get('phase_map') or {}).get('project_kind')!='bounded':return False
        # Ancestors only open the path to a mapped node. An explicit prerequisite
        # must also finish the same selected subtree that complete() checks.
        pending = [(nid, False) for nid in phase['node_instance_ids']]
        visited = set()
        while pending:
            current, must_complete = pending.pop()
            if (current, must_complete) in visited:
                continue
            if current == node_id:
                return True
            visited.add((current, must_complete))
            parent = self.parents.get(current)
            if parent:
                pending.append((parent, False))
            pending.extend((dep, True) for dep in self.nodes[current].get('requires', []))
            if must_complete and self.record_current(state, current):
                pending.extend((child, True) for child in self.completion_children(state, current))
        return False

    def check_open(self,state,node_id):
        require(node_id in self.active(state), 'NODE_NOT_ACTIVE:'+node_id)
        require(not self.blocked(node_id),'BLOCKED_ROUTE:'+node_id)
        if state.get('phase_map'):
            pid=self.phase_for(state,node_id)
            active_pid = state.get('active_phase_id')
            phase = state['phases'].get(active_pid)
            if pid is None:
                require(phase and self._bounded_prerequisite_node(state,phase,node_id),'PHASE_BOUNDARY:None')
            else:
                require(pid==active_pid,'PHASE_BOUNDARY:'+str(pid))
            # A stale bounded phase can recover its previously invalidated prerequisites manually.
            require(phase['status']=='ACTIVE' or (pid is None and phase['status']=='STALE'),'PHASE_GATE_REQUIRED')
            require(all(self.phase_current(state,d) for d in phase['dependency_ids']),'PHASE_DEPENDENCY_PENDING')
        for dep in self.node(node_id).get('requires',[]):
            require(self.complete(state,dep), 'PREREQUISITE_PENDING:'+dep)

    def context_next(self, state):
        self.check_state(state)
        pending = []
        awaiting = []
        for node_id in self.frontier(state):
            try:
                self.check_open(state, node_id)
            except GateError:
                continue
            if self.decision_awaiting_human(state, node_id):
                awaiting.append(node_id)
            else:
                pending.append(node_id)
        return {'project': state['project_id'], 'revision': state['revision'],
                'active_phase': state.get('active_phase_id'), 'pending_nodes': pending, 'awaiting_human': awaiting,
                'phase_status': state['phases'].get(state.get('active_phase_id'), {}).get('status'),
                'context_nodes': [node_id for node_id in pending if self.context_required(state, node_id)
                                  and assistance_action(state, self.node(node_id), 'analyze')['allowed']]}

    def context_required(self, state, node_id):
        return state.get('context_profile') == node_context.PROFILE and node_id == node_context.NODE

    def decision_awaiting_human(self, state, node_id):
        status = state['records'].get(node_id, {}).get('status')
        return status == 'AWAITING_HUMAN' or (status == 'DECIDED_DELEGATED' and self.context_required(state, node_id))

    def decision_delegation(self, state, node_id):
        gate = assistance_action(state, self.node(node_id), 'delegate')
        if self.context_required(state, node_id):
            return {**gate, 'allowed': False, 'basis': 'none', 'required_gate': 'node',
                    'stop_reason': 'CONTEXT_HUMAN_CONFIRMATION_REQUIRED'}
        return gate

    def retain_record_context(self, state, node_id):
        record = state['records'].get(node_id)
        packet = state.get('context_packets', {}).get(node_id)
        if record and packet and 'context_packet' not in record and record['proposal'].get('context_id') == digest(packet):
            record['context_packet'] = copy.deepcopy(packet)

    def context_identity(self, state, node_id):
        pins = self.contracts['source_reviews']
        return {'project': state['project_id'], 'node_id': node_id,
                'phase_id': self.phase_for(state, node_id), 'phase_map': state.get('phase_map_hash'),
                'policy': policy_hash(self.node(node_id), self.rules, self.contracts),
                'context': self.context_hash(state, node_id),
                'source_pins': {skill: {'commit': pins[skill]['commit'], 'git_blob': pins[skill]['git_blob'],
                                        'title': title} for skill, title in node_context.SKILL_SECTIONS.items()}}

    def check_context_action(self, state, node_id, action):
        permission = assistance_action(state, self.node(node_id), action)
        require(permission['allowed'], 'CONTEXT_ACTION_FORBIDDEN:'+str(permission['stop_reason']))

    def context_sections(self, state, node_id, required_titles):
        sections, required = [], {}
        for skill in self.skills_for(node_id):
            source = state['sources'].get(skill)
            require(source is not None, 'CONTEXT_SOURCE_MISSING:'+skill)
            reviewed = self.contracts['source_reviews'].get(skill, {})
            require(source['commit'] == reviewed.get('commit')
                    and source['git_blob'] == reviewed.get('git_blob'), 'CONTEXT_SOURCE_PIN_MISMATCH:'+skill)
            path = Path(self.artifact_path(state, source['path']))
            require(file_hash(path) == source['sha256'], 'SOURCE_BYTES_CHANGED')
            raw = path.read_bytes()
            git_blob = hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
            require(git_blob == reviewed['git_blob'], 'CONTEXT_SOURCE_PIN_MISMATCH:'+skill)
            rows = node_context.sections(skill, raw.decode('utf-8'))
            for row in rows:
                row.update(commit=source['commit'], git_blob=git_blob, url=source['url'])
            sections.extend(rows)
            for title in sorted(required_titles[skill]):
                matching = [row for row in rows if row['title'] == title]
                require(len(matching) == 1, f'CONTEXT_SECTION_MISSING_OR_AMBIGUOUS:{skill}#{title}')
                required[skill, title] = matching[0]
        return sections, required

    def open_context(self, state, node_id, index_path, *, query=None):
        require(self.context_required(state, node_id), 'CONTEXT_NODE_OUTSIDE_PILOT')
        self.check_open(state, node_id)
        require(not self.record_current(state, node_id), 'CONTEXT_NODE_ALREADY_DECIDED')
        require(not self.decision_awaiting_human(state, node_id), 'CONTEXT_NODE_AWAITING_HUMAN')
        self.check_context_action(state, node_id, 'analyze')
        identity = self.context_identity(state, node_id)
        grant = state.get('active_grant_id')
        require(identity['phase_id'] and grant, 'CONTEXT_ACTIVE_PHASE_REQUIRED')
        rules = [self.rules[rule_id] for rule_id in self.node(node_id)['rule_ids']]
        rule_sections = {rule['id']: [(rule['skill'], title.strip()) for title in rule['source_section'].split(';')]
                         for rule in rules}
        required_titles = {skill: {title} for skill, title in node_context.SKILL_SECTIONS.items()}
        for entries in rule_sections.values():
            for skill, title in entries:
                required_titles[skill].add(title)
        sections, required = self.context_sections(state, node_id, required_titles)
        required_rows = [row for row in sections if (row['skill_id'], row['title']) in required]
        facts = self.context_facts(state, node_id)
        for fact in facts.values():
            if fact.get('state') in ('PRESENT', 'ABSENT'):
                self.check_evidence(fact.get('evidence'), state)
        skill_rows = {skill: required[skill, title] for skill, title in node_context.SKILL_SECTIONS.items()}
        binding = {**identity, 'grant': grant,
                   'sections': {skill: {'id': row['id'], 'hash': digest(row), 'git_blob': row['git_blob']}
                                for skill, row in skill_rows.items()},
                   'criteria_sections': {rule_id: {required[key]['id']: digest(required[key]) for key in entries}
                                         for rule_id, entries in rule_sections.items()}}
        context_id = digest(binding)
        try:
            results = node_context.read_index(index_path, context_id, sections,
                                              tuple(row['id'] for row in required_rows), query)
        except (sqlite3.Error, ValueError) as error:
            raise GateError('CONTEXT_INDEX_UNAVAILABLE: '+str(error)) from error
        if query is not None:
            return {'context_id': context_id, 'matches': results}
        require(results == required_rows, 'CONTEXT_INDEX_REQUIRED_SECTIONS_MISSING')
        self.retain_record_context(state, node_id)
        state['context_packets'][node_id] = binding
        return {'context_id': context_id, 'packet': self.packet(state, node_id), 'scope': state['scope'],
                'facts': facts, 'required_sections': results, 'coverage': 'PACKET_PREPARED',
                'section_ids': {'skills': {skill: row['id'] for skill, row in skill_rows.items()},
                                'criteria': {rule_id: list(rows) for rule_id, rows in binding['criteria_sections'].items()}}}

    def check_context_application(self, state, node_id, proposal, binding):
        require(binding is not None and proposal.get('context_id') == digest(binding), 'CONTEXT_PACKET_REQUIRED')
        require(all(binding.get(k) == v for k, v in self.context_identity(state, node_id).items()),
                'CONTEXT_PACKET_STALE')
        for skill, section in binding['sections'].items():
            require(state['sources'][skill]['git_blob'] == section['git_blob'], 'CONTEXT_SOURCE_CHANGED')
        require(proposal['verification'] == 'OBSERVED', 'CONTEXT_OBSERVED_EVIDENCE_REQUIRED')
        captures = set()
        for ev in proposal['evidence']:
            raw = Path(self.artifact_path(state, ev['path'])).read_bytes()
            if hashlib.sha256(raw).hexdigest() == ev['sha256'] and node_context.is_png(raw):
                captures.add(ev['path'])
        require(bool(captures), 'CONTEXT_CAPTURE_REQUIRED')
        for review in proposal['skill_reviews']:
            skill = review['skill_id']
            require(review.get('section_id') == binding['sections'][skill]['id'],
                    'CONTEXT_APPLICATION_REQUIRED:'+skill)
        criteria_sections = binding.get('criteria_sections')
        for review in proposal['criterion_reviews']:
            rule_id = review['rule_id']
            if criteria_sections is None:
                skill = self.rules[rule_id]['skill']
                linked = review.get('section_id') == binding['sections'][skill]['id']
            else:
                expected = criteria_sections[rule_id]
                section_ids = review.get('section_ids')
                linked = (isinstance(section_ids, list) and len(section_ids) == len(expected)
                          and all(isinstance(section_id, str) for section_id in section_ids)
                          and set(section_ids) == set(expected))
            require(linked, 'CONTEXT_APPLICATION_REQUIRED:'+rule_id)
        for review in proposal['skill_reviews'] + proposal['criterion_reviews']:
            require(nonblank(review.get('observation')) and captures.intersection(review['evidence_refs']),
                    'CONTEXT_OBSERVATION_AND_CAPTURE_REQUIRED')

    def confirm_structure(self,state,node_id,receipt):
        self.check_open(state,node_id)
        r=human_receipt(receipt,self.structure_hash(node_id),'structure')
        state['structures'][node_id]={'status':'CONFIRMED','hash':self.structure_hash(node_id),'receipt':r}
        state['history'].append({'event':'structure_confirmed','node_id':node_id,'receipt':r})

    def register_source(self,state,skill_id,path,commit,expected_git_blob,source_ref):
        self.check_state(state)
        require(skill_id in self.inventory,'UNKNOWN_SKILL')
        require(commit==self.inventory[skill_id]['candidate_commit'],'SOURCE_COMMIT_MISMATCH')
        require(nonblank(source_ref),'SOURCE_REFERENCE_REQUIRED')
        h=file_hash(path);data=Path(path).read_bytes()
        blob=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
        require(blob==expected_git_blob,'SOURCE_BLOB_MISMATCH')
        text=data.decode('utf-8')
        review=self.contracts.get('source_reviews',{}).get(skill_id,{})
        policy=review.get('invocation_policy','UNKNOWN') if review.get('git_blob')==blob else 'UNKNOWN'
        explicit=True if policy=='EXPLICIT' else False if policy=='IMPLICIT_ALLOWED' else None
        old=state['sources'].get(skill_id)
        if old and old['sha256']!=h:
            for nid,rec in list(state['records'].items()):
                if skill_id in rec.get('source_hashes',{}):self.invalidate(state,nid,'Source bytes changed')
        state['sources'][skill_id]={'path':str(Path(path).resolve()),'sha256':h,'git_blob':blob,
            'commit':commit,'source_ref':source_ref,'url':self.inventory[skill_id]['source_url'],
            'explicit_invocation_required':explicit,'invocation_policy_verified':explicit is not None,'coverage':'BYTES_RECEIVED_NOT_COMPREHENSION',
            'recorded_at':now()}

    def artifact_path(self,state,path):
        return (state or {}).get('artifact_paths',{}).get(path,path)

    def bind_evidence_paths(self, state, evidence):
        # Keep references used in proposal hashes intact; resume rebinds these same keys.
        for entry in evidence:
            path = Path(entry['path'])
            if not path.is_absolute():
                state.setdefault('artifact_paths', {}).setdefault(entry['path'], str(path.absolute()))

    def check_evidence(self,evidence,state=None):
        require(isinstance(evidence,list) and evidence,'EVIDENCE_REQUIRED')
        for e in evidence:
            require(isinstance(e,dict) and nonblank(e.get('note')), 'EVIDENCE_NOTE_REQUIRED')
            try:valid=file_hash(self.artifact_path(state,e.get('path','')))==e.get('sha256')
            except (GateError,TypeError,OSError):valid=False
            require(valid,'EVIDENCE_CHANGED_OR_MISSING')

    def check_requirements(self,node_id):
        n=self.node(node_id)
        return [r for r in self.contracts.get('verification_requirements',[])
                if node_id in r['applies_to'] or n['definition_id'] in r['applies_to']]

    def check_outcomes(self,state,node_id,proposal):
        """Inspect bound check outcomes, preserving method/outcome distinction.

        Failing outcomes are valid diagnostic data, not validation failures;
        external file bytes are re-read on every gate evaluation.
        """
        reqs=self.check_requirements(node_id)
        refs={e['path'] for e in proposal.get('evidence',[]) if isinstance(e,dict)}
        refs.update(state['sources'][skill_id]['source_ref']
                    for skill_id in self.skills_for(node_id)
                    if isinstance(state['sources'].get(skill_id),dict)
                    and isinstance(state['sources'][skill_id].get('source_ref'),str))
        results=proposal.get('verification_results')
        issues=validate_results(results,reqs,refs)
        require(not issues,'CHECK_RESULTS_INVALID:'+','.join(x['code'] for x in issues))
        for item in (results or {}).get('checks',[]):
            if item.get('evidence_refs'):self.resolve_refs(state,item['evidence_refs'])
        return evaluate_results(results or {'schema':'design-tree-checks/1','checks':[]},reqs,state.get('facts',{}))

    def check_gate(self,state,node_id,proposal):
        require(proposal.get('verification')!='NOT_VERIFIED','PHASE_VERIFICATION_PENDING')
        evaluation=self.check_outcomes(state,node_id,proposal)
        require(not evaluation['blocking_ids'],'CHECK_REQUIRED_PENDING:'+','.join(evaluation['blocking_ids']))
        return evaluation

    def audit_intent(self,state):
        # Conservatively preserve an explicit audit choice until that question is
        # revised. Never mutate global mode after binding a proposal to it.
        if state.get('mode')=='audit':return True
        for nid,rec in state.get('records',{}).items():
            if self.nodes.get(nid,{}).get('definition_id')=='ENV02':
                chosen=rec.get('proposal',{}).get('selected')
                if isinstance(chosen,str) and chosen.endswith('ENV02_2'):return True
        return False

    def validate_proposal(self,state,node_id,p,*,context_packet=None):
        require(isinstance(p,dict) and nonblank(p.get('summary')),'DECISION_SUMMARY_REQUIRED')
        n=self.node(node_id)
        choices=[c['node']['id'] for c in n['children']]
        if n['kind']=='decision': require(p.get('selected') in choices,'SELECTION_REQUIRED')
        else:require(p.get('selected') is None,'ALL_OR_RESULT_CANNOT_SELECT_ONE')
        alts=p.get('alternatives',[])
        require(isinstance(alts,list) and all(isinstance(a,dict) for a in alts) and len(alts)==len(choices) and {a.get('node_id') for a in alts}==set(choices),'ALTERNATIVES_COVERAGE_REQUIRED')
        for a in alts:
            expected='REQUIRED' if n['kind']=='all' else 'SELECTED' if a['node_id']==p.get('selected') else 'REJECTED'
            require(a.get('disposition')==expected and nonblank(a.get('reason')),'ALTERNATIVES_DISPOSITION_INVALID')
        skills=self.skills_for(node_id);reviews=p.get('skill_reviews',[])
        require(isinstance(reviews,list) and all(isinstance(r,dict) for r in reviews) and len(reviews)==len(skills) and {r.get('skill_id') for r in reviews}==set(skills),'SKILL_COVERAGE_REQUIRED')
        for r in reviews:
            require(r.get('status') in ('APPLIED','REVIEWED_NOT_APPLICABLE') and nonblank(r.get('rationale')) and bool(r.get('evidence_refs')),'SKILL_REVIEW_INCOMPLETE')
            sr=state['sources'].get(r['skill_id'])
            require(sr is not None,'SOURCE_NOT_RETRIEVED')
            try:valid=file_hash(self.artifact_path(state,sr['path']))==sr['sha256']
            except (GateError,OSError):valid=False
            require(valid,'SOURCE_BYTES_CHANGED')
            require(r.get('use','REFERENCE_ONLY')=='REFERENCE_ONLY','SOURCE_INVOCATION_NOT_AUTHORIZED_BY_HELPER')
        rule_ids=set(n.get('rule_ids',[]))
        cr=p.get('criterion_reviews',[])
        require(isinstance(cr,list) and all(isinstance(r,dict) for r in cr) and len(cr)==len(rule_ids) and {r.get('rule_id') for r in cr}==rule_ids,'CRITERION_COVERAGE_REQUIRED')
        for review in cr:
            require(review.get('disposition') in ('APPLIED','NOT_APPLICABLE') and nonblank(review.get('reason')) and review.get('evidence_refs'),'CRITERION_DECISION_REQUIRED')
        self.check_evidence(p.get('evidence'),state)
        evidence_paths={e['path'] for e in p['evidence']}
        source_refs={sr['source_ref'] for sid,sr in state['sources'].items() if sid in skills}
        allowed_refs=evidence_paths | source_refs
        for review in reviews + cr:
            refs=review.get('evidence_refs')
            require(isinstance(refs,list) and refs and all(nonblank(ref) and ref in allowed_refs for ref in refs),
                    'EVIDENCE_REFERENCE_UNRESOLVED')
        require(p.get('verification') in ('OBSERVED','STATIC','NOT_VERIFIED'),'VERIFICATION_STATE_REQUIRED')
        self.check_outcomes(state,node_id,p)
        require(p.get('permission') in ('read_only','write'),'PERMISSION_REQUIRED')
        if self.audit_intent(state) or n.get('write_policy')=='READ_ONLY':
            require(p.get('permission')=='read_only','AUDIT_WRITE_FORBIDDEN')
        key=n.get('candidate_key')
        if key:
            cand=p.get('candidate')
            require(isinstance(cand,dict) and cand.get('candidate_key')==key,'CANDIDATE_KEY_MISMATCH')
            require(all(nonblank(cand.get(k)) for k in ('component_id','requirement_id','candidate_source','candidate_version')),'CANDIDATE_IDENTITY_REQUIRED')
            bound=state['candidates'].get(key)
            require(bound is None or bound==cand,'CANDIDATE_CONTEXT_MISMATCH')
        selected=p.get('selected_relations',[])
        known={r['id'] for r in self.contracts['relations'] if node_id in r['applies_to'] or n['definition_id'] in r['applies_to']}
        require(isinstance(selected,list) and all(isinstance(x,str) for x in selected) and set(selected)<=known,'UNKNOWN_RELATION_SELECTION')
        evaluated=evaluate_contracts(n,{'facts':state.get('facts',{}),'operation':'reference',
                                      'selected_relations':selected},self.contracts)
        require(not evaluated['pending'],'CONTRACT_CONDITION_UNKNOWN:'+','.join(evaluated['pending']))
        relations=p.get('relation_reviews',[])
        required=set(evaluated['obligations'])
        require(isinstance(relations,list) and all(isinstance(r,dict) for r in relations) and len(relations)==len(required) and {r.get('relation_id') for r in relations}==required,'RELATION_COVERAGE_REQUIRED')
        for review in relations:
            require(review.get('status')=='SATISFIED' and nonblank(review.get('reason')),'RELATION_REVIEW_REQUIRED')
            refs=review.get('evidence_refs')
            require(isinstance(refs,list) and refs and all(x in allowed_refs for x in refs),'RELATION_EVIDENCE_REQUIRED')
            rel=next(x for x in self.contracts['relations'] if x['id']==review['relation_id'])
            if rel['target']['kind']=='skill':
                require(any(r['skill_id']==rel['target']['id'] for r in reviews),'DELEGATED_DOMAIN_NOT_REVIEWED')
            else:
                resource=next(x for x in self.contracts['resources'] if x['id']==rel['target']['id'])
                require(review.get('resource_id')==resource['id'] and nonblank(review.get('resource_path')),'RESOURCE_IDENTITY_REQUIRED')
                path=review['resource_path']
                ev=next((e for e in p['evidence'] if e['path']==path),None)
                require(ev is not None and path in refs,'RESOURCE_EVIDENCE_REQUIRED')
                # Resource bytes must be the pinned reference, not another file
                # that happens to exist in the proposal's evidence list.
                if resource.get('sha256'):
                    require(ev['sha256']==resource['sha256'],'RESOURCE_BYTES_MISMATCH')
                elif resource.get('git_blob'):
                    data=Path(self.artifact_path(state,path)).read_bytes()
                    blob=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
                    require(blob==resource['git_blob'],'RESOURCE_BYTES_MISMATCH')
                else:raise GateError('RESOURCE_PIN_REQUIRED')
        for fid in evaluated['fact_ids']:
            fact=state.get('facts',{}).get(fid)
            if fact and fact.get('state') in ('PRESENT','ABSENT'):self.check_evidence(fact.get('evidence'),state)
        if self.context_required(state, node_id):
            packet = state['context_packets'].get(node_id) if context_packet is None else context_packet
            self.check_context_application(state, node_id, p, packet)
        return True

    def propose(self,state,node_id,proposal):
        self.check_open(state,node_id)
        require(self.structure_confirmed(state,node_id),'STRUCTURE_CONFIRMATION_REQUIRED')
        packet = None
        if self.context_required(state, node_id):
            require(not self.record_current(state, node_id), 'CONTEXT_NODE_ALREADY_DECIDED')
            require(not self.decision_awaiting_human(state, node_id), 'CONTEXT_NODE_AWAITING_HUMAN')
            packet = state['context_packets'].get(node_id)
            require(packet is None or 'criteria_sections' in packet, 'CONTEXT_PACKET_REOPEN_REQUIRED')
        self.validate_proposal(state,node_id,proposal)
        if packet is not None:
            self.check_context_action(state, node_id, 'draft')
            require(packet['grant'] == state.get('active_grant_id'), 'CONTEXT_PACKET_GRANT_STALE')
        self.bind_evidence_paths(state, proposal['evidence'])
        if node_id in state['records']:
            state['history'].append({'event':'proposal_replaced','node_id':node_id,'record':copy.deepcopy(state['records'][node_id]),'at':now()})
            self.invalidate(state,node_id,'Proposal revision')
        authority={'decided_by':'human','grant_id':None,'grant_hash':None}
        if self.decision_delegation(state,node_id)['allowed']:
            g=state['grants'][state['active_grant_id']]
            authority={'decided_by':'agent_delegated','grant_id':g['id'],'grant_hash':g['authorization_hash']}
        p=copy.deepcopy(proposal)
        binding=self.binding(state,node_id,authority)
        h=digest({'binding':binding,'proposal':p})
        state['records'][node_id]={'status':'AWAITING_HUMAN','proposal':p,'proposal_hash':h,
            'source_hashes':{sid:state['sources'][sid]['sha256'] for sid in self.skills_for(node_id)},
            'binding':binding,'authority':authority,'submitted_at':now()}
        if packet is not None:
            state['records'][node_id]['context_packet'] = copy.deepcopy(packet)
        if self.node(node_id).get('candidate_key'):
            state['candidates'][self.node(node_id)['candidate_key']]=copy.deepcopy(p['candidate'])
        state['history'].append({'event':'proposal','node_id':node_id,'hash':h,'at':now()})
        return h

    def confirm_decision(self,state,node_id,receipt):
        self.check_open(state,node_id)
        rec=state['records'].get(node_id,{})
        require(rec.get('status') in ('AWAITING_HUMAN','DECIDED_DELEGATED'),'PROPOSAL_REQUIRED')
        self.validate_proposal(state,node_id,rec['proposal'],context_packet=rec.get('context_packet'))
        self.check_gate(state,node_id,rec['proposal'])
        require(self.record_data_valid(state,node_id),'PROPOSAL_STALE')
        r=human_receipt(receipt,rec['proposal_hash'],'project')
        self.retain_record_context(state, node_id)
        rec['status']='APPROVED';rec['receipt']=r
        rec['authority']['acceptance_ref']=r['message_ref']
        state['history'].append({'event':'decision_confirmed','node_id':node_id,'receipt':r})
        # Audit intent is enforced per scoped tree context and proposal, not by
        # mutating global mode after a proposal was bound to it.

    @read_snapshot
    def record_current(self,state,node_id):
        rec=state['records'].get(node_id,{})
        if rec.get('status') not in ('APPROVED','DECIDED_DELEGATED','RATIFIED_IN_PHASE'):return False
        if not self.record_data_valid(state,node_id):return False
        try:
            if rec['status']=='APPROVED':
                human_receipt(rec.get('receipt'),rec['proposal_hash'],'project')
            elif rec['status']=='DECIDED_DELEGATED':
                require(not self.context_required(state, node_id), 'CONTEXT_HUMAN_CONFIRMATION_REQUIRED')
                gid=rec['authority'].get('grant_id');g=state['grants'].get(gid,{})
                pid=self.phase_for(state,node_id)
                require(gid==state.get('active_grant_id') and g.get('status')=='ACTIVE','DELEGATION_REVOKED')
                require(state['phases'][pid]['status'] in ('ACTIVE','AWAITING_HUMAN'),'PHASE_NOT_ACTIVE')
                require(g['scope_hash']==self.scope_hash(state),'DELEGATION_CONTEXT_CHANGED')
                require(node_id not in g.get('reserved_decisions',[]),'RESERVED_DECISION')
            else:
                pid=rec.get('phase_acceptance_id');phase=state['phases'].get(pid,{})
                require(phase.get('status')=='ACCEPTED','PHASE_NOT_ACCEPTED')
                require(phase.get('packet',{}).get('records',{}).get(node_id)==rec['proposal_hash'],'PHASE_RECORD_MISMATCH')
                human_receipt(phase.get('acceptance'),phase.get('gate_packet_hash'),'phase')
                require(digest(phase.get('packet'))==phase.get('gate_packet_hash'),'PHASE_PACKET_CHANGED')
                self.check_evidence(phase.get('delivered'),state)
            if state.get('phase_map'):
                pid=self.phase_for(state,node_id)
                if pid is not None:
                    require(all(self.phase_current(state,d) for d in state['phases'][pid]['dependency_ids']),'PHASE_DEPENDENCY_STALE')
                else:
                    require(rec['status']=='APPROVED' and state['phase_map'].get('project_kind')=='bounded','NODE_OUTSIDE_PHASE_MAP')
            return True
        except (GateError,KeyError,OSError,TypeError,ValueError):return False

    def scope_hash(self,state):
        return digest({k:state.get(k) for k in ('project_id','scope','medium','mode')})

    def context_facts(self,state,node_id):
        n=self.node(node_id)
        needed={p['fact'] for r in self.contracts.get('relations',[]) if n['definition_id'] in r.get('applies_to',[]) or node_id in r.get('applies_to',[]) for p in r['when']}
        needed.update(p['fact'] for r in self.check_requirements(node_id) for p in r['when'])
        facts={}
        for fid,f in state.get('facts',{}).items():
            if fid in needed or '*' in f.get('applies_to',[]) or node_id in f.get('applies_to',[]) or n['definition_id'] in f.get('applies_to',[]):
                facts[fid]={k:v for k,v in f.items() if k not in ('comment','observed_at')}
        return facts

    def context_hash(self,state,node_id):
        return digest({'scope':self.scope_hash(state),'facts':self.context_facts(state,node_id)})

    def binding(self,state,node_id,authority):
        return {'structure':self.structure_hash(node_id),'policy':policy_hash(self.node(node_id),self.rules,self.contracts),
                'context':self.context_hash(state,node_id),'project':state['project_id'],
                'authority':{k:authority.get(k) for k in ('decided_by','grant_id','grant_hash')}}

    @read_snapshot
    def record_data_valid(self,state,node_id):
        try:
            rec=state['records'][node_id];require(self.structure_confirmed(state,node_id),'STRUCTURE_CHANGED')
            self.validate_proposal(state,node_id,rec['proposal'],context_packet=rec.get('context_packet'))
            n=self.node(node_id)
            needed={p['fact'] for r in self.contracts.get('relations',[]) if n['definition_id'] in r.get('applies_to',[]) or node_id in r.get('applies_to',[]) for p in r['when']}
            needed.update(p['fact'] for r in self.check_requirements(node_id) for p in r['when'])
            for fid,f in state.get('facts',{}).items():
                if fid in needed or '*' in f.get('applies_to',[]) or node_id in f.get('applies_to',[]) or n['definition_id'] in f.get('applies_to',[]):
                    if f.get('state') in ('PRESENT','ABSENT'):self.check_evidence(f.get('evidence'),state)
            expected={sid:state['sources'][sid]['sha256'] for sid in self.skills_for(node_id)}
            require(rec.get('source_hashes')==expected,'SOURCE_SET_CHANGED')
            authority=rec['authority'];require(authority.get('decided_by') in ('human','agent_delegated'),'AUTHORITY_INVALID')
            if authority.get('decided_by')=='agent_delegated':
                g=state['grants'][authority['grant_id']]
                require(authority.get('grant_hash')==g['authorization_hash'],'DELEGATION_CHANGED')
                human_receipt(g.get('receipt'),g['authorization_hash'],'delegation')
                require(self.grant_hash(state,g)==g['authorization_hash'],'DELEGATION_CONTEXT_CHANGED')
            b=self.binding(state,node_id,authority)
            require(rec.get('binding')==b and rec.get('proposal_hash')==digest({'binding':b,'proposal':rec['proposal']}),'PROPOSAL_CHANGED')
            return True
        except (GateError,KeyError,TypeError,ValueError,OSError):return False

    def structure_set_hash(self,node_ids):
        require(isinstance(node_ids,list) and node_ids and len(node_ids)==len(set(node_ids)),'STRUCTURE_SET_INVALID')
        return digest({nid:self.structure_hash(nid) for nid in sorted(node_ids)})

    def confirm_structure_set(self,state,node_ids,receipt):
        self.check_state(state);h=self.structure_set_hash(node_ids)
        r=human_receipt(receipt,h,'structure_set')
        state['structure_sets'][h]={'nodes':{nid:self.structure_hash(nid) for nid in node_ids},'receipt':r}

    @read_snapshot
    def structure_confirmed(self,state,node_id):
        st=state.get('structures',{}).get(node_id,{})
        h=self.structure_hash(node_id)
        try:
            if st.get('status')=='CONFIRMED' and st.get('hash')==h:
                human_receipt(st.get('receipt'),h,'structure');return True
            for key,group in state.get('structure_sets',{}).items():
                if group.get('nodes',{}).get(node_id)==h and digest(group['nodes'])==key:
                    human_receipt(group.get('receipt'),key,'structure_set');return True
        except (GateError,KeyError,TypeError):return False
        return False

    def resolve_refs(self,state,refs):
        require(isinstance(refs,list) and refs and all(nonblank(x) for x in refs),'EVIDENCE_REFERENCE_REQUIRED')
        sources = {}
        for source in state['sources'].values():
            sources.setdefault(source['source_ref'], set()).add((source['path'], source['sha256']))
        result = []
        for ref in sorted(set(refs)):
            candidates = sources.get(ref, set())
            require(len(candidates) <= 1, 'EVIDENCE_REFERENCE_AMBIGUOUS:' + ref)
            path, expected = next(iter(candidates), (ref, None))
            try:h=file_hash(self.artifact_path(state,path))
            except (GateError,OSError,TypeError):raise GateError('EVIDENCE_REFERENCE_UNRESOLVED:'+ref)
            require(expected is None or expected==h,'EVIDENCE_CHANGED_OR_MISSING')
            result.append({'ref': ref, 'path': path, 'sha256': h})
        return result

    def set_fact(self,state,fact_id,fact):
        self.check_state(state);require(nonblank(fact_id) and isinstance(fact,dict),'FACT_INVALID')
        require(fact.get('state') in ('PRESENT','ABSENT','UNKNOWN'),'FACT_STATE_INVALID')
        require(fact.get('scope') in ('project','component','requirement','host'),'FACT_SCOPE_INVALID')
        require(nonblank(fact.get('subject')) and type(fact.get('revision')) is int and fact['revision']>0,'FACT_IDENTITY_REQUIRED')
        require(isinstance(fact.get('applies_to'),list) and fact['applies_to'] and all(isinstance(x,str) for x in fact['applies_to']) and set(fact['applies_to']) <= (set(self.nodes)|{n['definition_id'] for n in self.nodes.values()}|{'*'}),'FACT_BINDING_REQUIRED')
        if fact['state']=='PRESENT':require('value' in fact,'FACT_VALUE_REQUIRED')
        if fact['state']!='UNKNOWN':self.check_evidence(fact.get('evidence'),state)
        previous=state['facts'].get(fact_id)
        require(previous is None or fact['revision']>previous['revision'],'FACT_REVISION_CONFLICT')
        self.bind_evidence_paths(state, fact.get('evidence', []))
        before={nid:self.context_hash(state,nid) for nid in state['records']}
        state['facts'][fact_id]=copy.deepcopy(fact)
        state['facts'][fact_id]['evidence_refs']=[e['path'] for e in fact.get('evidence',[])]
        affected=[]
        for nid,h in before.items():
            if h!=self.context_hash(state,nid):affected+=self.invalidate(state,nid,'Relevant fact changed: '+fact_id)
        state['history'].append({'event':'fact_updated','fact_id':fact_id,'previous':previous,'at':now()})
        return sorted(set(affected))

    def phase_family(self,node_id):
        ancestors=[];cur=node_id
        while cur:
            ancestors.append(self.nodes[cur]['definition_id']);cur=self.parents.get(cur)
        if 'QA01' in ancestors:return 'review'
        if 'R01' in ancestors:return 'components'
        if 'D00' in ancestors:return 'visual'
        return 'foundations'

    def default_phase_map(self):
        descriptions={'foundations':'Producto, contexto y restricciones','visual':'Muestras y sistema visual','components':'Selección y adopción de componentes','review':'Informe y evidencias de conjunto'}
        phases=[];previous=[]
        for family,title in descriptions.items():
            phases.append({'id':family,'revision':1,'family':family,'node_instance_ids':[nid for nid in self.nodes if self.phase_family(nid)==family],
                           'dependency_ids':list(previous),'deliverables':[title]})
            previous=[family]
        return {'schema':'design-tree-phases/1','project_kind':'multi_phase','phases':phases}

    def configure_phases(self,state,phase_map,receipt):
        self.check_state(state)
        require(not state.get('phase_map'),'PHASE_MAP_ALREADY_CONFIGURED')
        require(isinstance(phase_map,dict) and phase_map.get('schema')=='design-tree-phases/1','PHASE_MAP_INVALID')
        phases=phase_map.get('phases',[]);kind=phase_map.get('project_kind')
        require(kind in ('bounded','multi_phase') and isinstance(phases,list) and phases,'PHASE_MAP_INVALID')
        if kind=='multi_phase':require(len(phases)>=2,'ONE_SHOT_FORBIDDEN')
        seen=set();covered=set()
        for p in phases:
            require(nonblank(p.get('id')) and p['id'] not in seen,'PHASE_ID_INVALID')
            ids=p.get('node_instance_ids');deps=p.get('dependency_ids')
            require(isinstance(ids,list) and ids and len(ids)==len(set(ids)) and not set(ids)-set(self.nodes),'PHASE_NODES_INVALID')
            require(not covered.intersection(ids),'PHASE_OVERLAP')
            families={self.phase_family(nid) for nid in ids}
            require(len(families)==1 and p.get('family') in families,'PHASE_DOMAIN_FUSION_FORBIDDEN')
            require(isinstance(deps,list) and set(deps)<=seen,'PHASE_DEPENDENCY_ORDER_INVALID')
            require(isinstance(p.get('deliverables'),list) and p['deliverables'] and all(nonblank(d) for d in p['deliverables']),'PHASE_OUTPUT_REQUIRED')
            require(type(p.get('revision')) is int and p['revision']>0,'PHASE_REVISION_INVALID')
            seen.add(p['id']);covered.update(ids)
        if kind=='multi_phase':require(covered==set(self.nodes),'PHASE_COVERAGE_REQUIRED')
        h=digest(phase_map);r=human_receipt(receipt,h,'phase_map')
        state['phase_map']=copy.deepcopy(phase_map);state['phase_map_hash']=h;state['phase_map_receipt']=r
        state['phases']={p['id']:{**copy.deepcopy(p),'status':'PLANNED','grant_id':None,'delivered':[],'gate_packet_hash':None} for p in phases}

    def phase_for(self,state,node_id):
        return next((pid for pid,p in state.get('phases',{}).items() if node_id in p['node_instance_ids']),None)

    def grant_template(self,state,phase_id,level='manual'):
        require(phase_id in state['phases'],'UNKNOWN_PHASE')
        return {'id':'grant-'+str(len(state['grants'])+1),'revision':1,'level':level,'scope_id':state['project_id'],
                'scope_hash':self.scope_hash(state),'phase_map_hash':state['phase_map_hash'],'phase_id':phase_id,
                'allowed_actions':['analyze','compare','draft','test'],'reserved_decisions':[],'stop_at':phase_id,
                'message_ref':'REPLACE_WITH_USER_MESSAGE','quote':'REPLACE_WITH_USER_WORDS'}

    def grant_hash(self,state,grant):
        fields=('id','revision','level','scope_id','scope_hash','phase_map_hash','phase_id','allowed_actions','reserved_decisions','stop_at','message_ref','quote')
        return digest({'scope':self.scope_hash(state),'phase_map':state['phase_map_hash'],'grant':{k:grant.get(k) for k in fields}})

    def grant_assistance(self,state,grant,receipt):
        self.check_state(state);require(not validate_assistance(grant,state.get('phase_map') or {}),'ASSISTANCE_GRANT_INVALID')
        require(grant['id'] not in state['grants'],'GRANT_ID_ALREADY_USED')
        require(grant['scope_id']==state['project_id'] and grant['scope_hash']==self.scope_hash(state),'GRANT_SCOPE_MISMATCH')
        require(grant['phase_map_hash']==state['phase_map_hash'] and grant['phase_id']==grant['stop_at'],'GRANT_PHASE_MISMATCH')
        pid=grant['phase_id'];phase=state['phases'][pid]
        require(phase['status'] in ('PLANNED','ACTIVE','BLOCKED','STALE'),'PHASE_CANNOT_START')
        require(all(self.phase_current(state,d) for d in phase['dependency_ids']),'PHASE_DEPENDENCY_PENDING')
        oldphase=state.get('active_phase_id')
        if oldphase and oldphase!=pid:require(self.phase_current(state,oldphase),'PHASE_GATE_PENDING')
        h=self.grant_hash(state,grant);r=human_receipt(receipt,h,'delegation')
        old=state.get('active_grant_id')
        if old:state['grants'][old]['status']='REVOKED'
        state['grants'][grant['id']]={**copy.deepcopy(grant),'status':'ACTIVE','authorization_hash':h,'receipt':r}
        state['active_grant_id']=grant['id'];state['assistance_level']=grant['level'];state['active_phase_id']=pid
        phase['grant_id']=grant['id'];phase['status']='ACTIVE';phase['gate_packet_hash']=None
        state['history'].append({'event':'delegation_started','grant_id':grant['id'],'at':now()})

    def revoke_delegation(self,state,reason):
        require(nonblank(reason),'REVOCATION_REASON_REQUIRED')
        gid=state.get('active_grant_id')
        if gid:state['grants'][gid]['status']='REVOKED'
        state['active_grant_id']=None;state['assistance_level']='manual'
        state['history'].append({'event':'delegation_revoked','grant_id':gid,'reason':reason,'at':now()})

    def delegate_decision(self,state,node_id):
        self.check_open(state,node_id)
        gate=self.decision_delegation(state,node_id)
        require(gate['allowed'],gate['stop_reason'] or 'DELEGATION_FORBIDDEN')
        rec=state['records'].get(node_id,{})
        require(rec.get('status')=='AWAITING_HUMAN' and rec.get('authority',{}).get('decided_by')=='agent_delegated','DELEGATED_PROPOSAL_REQUIRED')
        active_gid=state.get('active_grant_id')
        active_grant=state['grants'].get(active_gid,{})
        require(rec['authority'].get('grant_id')==active_gid and active_grant.get('status')=='ACTIVE'
                and rec['authority'].get('grant_hash')==active_grant.get('authorization_hash'),'DELEGATION_REVOKED')
        require(self.record_data_valid(state,node_id),'PROPOSAL_STALE')
        rec['status']='DECIDED_DELEGATED'
        state['history'].append({'event':'decided_delegated','node_id':node_id,'grant_id':active_gid,'at':now()})

    @read_snapshot
    def phase_current(self,state,phase_id):
        try:
            phase=state['phases'][phase_id];require(phase['status']=='ACCEPTED','PHASE_NOT_ACCEPTED')
            packet=phase['packet'];require(digest(packet)==phase['gate_packet_hash'],'PHASE_PACKET_CHANGED')
            human_receipt(phase['acceptance'],phase['gate_packet_hash'],'phase')
            require(packet['scope_hash']==self.scope_hash(state) and packet['phase_map_hash']==state['phase_map_hash'],'PHASE_CONTEXT_CHANGED')
            self.check_evidence(phase['delivered'],state)
            require(packet['deliverables']==phase['delivered'],'PHASE_DELIVERABLES_CHANGED')
            for nid,h in packet['records'].items():
                require(state['records'][nid]['proposal_hash']==h and self.record_data_valid(state,nid),'PHASE_DECISION_STALE')
                self.check_gate(state,nid,state['records'][nid]['proposal'])
                require(state['records'][nid]['status'] in ('APPROVED','RATIFIED_IN_PHASE'),'PHASE_DECISION_NOT_ACCEPTED')
            return all(self.phase_current(state,d) for d in phase['dependency_ids'])
        except (GateError,KeyError,ValueError,TypeError,OSError,RecursionError):return False

    def prepare_phase(self,state,phase_id,deliverables):
        self.check_state(state);phase=state['phases'].get(phase_id,{})
        require(phase_id==state.get('active_phase_id') and phase.get('status') in ('ACTIVE','AWAITING_HUMAN'),'PHASE_NOT_ACTIVE')
        proposal = state.get('inventory_proposal')
        pending = phase['status']=='AWAITING_HUMAN'
        if pending:
            require(proposal and phase.get('packet',{}).get('inventory_hash'),'PHASE_NOT_ACTIVE')
            # Before evidence bindings, an inventory digest covered only these three fields.
            legacy_hash = digest({'baseline':self.inventory_hash,'rows':proposal['rows'],'context':self.scope_hash(state)})
            require(phase['packet']['inventory_hash']==legacy_hash and proposal['hash']!=legacy_hash,'PHASE_NOT_ACTIVE')
        act=self.active(state);ids=[nid for nid in act if nid in phase['node_instance_ids']]
        require(ids and all(self.record_current(state,nid) and not self.blocked(nid) for nid in ids),'PHASE_OBLIGATIONS_PENDING')
        for nid in ids:self.check_gate(state,nid,state['records'][nid]['proposal'])
        self.check_evidence(deliverables,state)
        require(len(deliverables)>=len(phase['deliverables']),'PHASE_DELIVERABLES_MISSING')
        inventory_hash = self.checked_inventory_hash(state, proposal) if proposal else None
        packet={'phase_id':phase_id,'revision':phase['revision'],'phase_map_hash':state['phase_map_hash'],'scope_hash':self.scope_hash(state),
                'records':{nid:state['records'][nid]['proposal_hash'] for nid in sorted(ids)},'deliverables':copy.deepcopy(deliverables),
                'grant_id':phase.get('grant_id'),'inventory_hash':inventory_hash}
        if pending:
            previous = {**packet, 'inventory_hash':legacy_hash}
            require(phase['packet']==previous and phase['gate_packet_hash']==digest(previous)
                    and phase['delivered']==deliverables,'PHASE_NOT_ACTIVE')
            state['history'].append({'event':'phase_inventory_binding_upgraded','phase_id':phase_id,
                                     'previous':copy.deepcopy(phase),'at':now()})
        self.bind_evidence_paths(state, deliverables)
        h=digest(packet);phase.update(status='AWAITING_HUMAN',packet=packet,gate_packet_hash=h,delivered=copy.deepcopy(deliverables))
        return {'gate_packet_hash':h,'packet':packet,'decisions':[{'node_id':nid,**copy.deepcopy(state['records'][nid])} for nid in ids],
                'notice':'One phase acceptance; no individual human receipts are fabricated.'}

    def accept_phase(self,state,phase_id,receipt):
        # Validate every field before committing any ratification.
        work=copy.deepcopy(state);phase=work['phases'].get(phase_id,{})
        require(phase.get('status')=='AWAITING_HUMAN','PHASE_GATE_REQUIRED')
        packet=phase['packet'];h=phase['gate_packet_hash'];r=human_receipt(receipt,h,'phase')
        require(digest(packet)==h and packet['scope_hash']==self.scope_hash(work),'PHASE_PACKET_STALE')
        self.check_evidence(phase['delivered'],work)
        require(packet['deliverables']==phase['delivered'],'PHASE_DELIVERABLES_CHANGED')
        ids=[nid for nid in self.active(work) if nid in phase['node_instance_ids']]
        require(set(ids)==set(packet['records']) and all(self.record_current(work,nid) and packet['records'][nid]==work['records'][nid]['proposal_hash'] for nid in ids),'PHASE_PACKET_STALE')
        for nid in ids:self.check_gate(work,nid,work['records'][nid]['proposal'])
        ip=work.get('inventory_proposal')
        if packet.get('inventory_hash'):
            require(ip and self.checked_inventory_hash(work, ip) == packet['inventory_hash'], 'INVENTORY_CHANGED')
        for nid in ids:
            rec=work['records'][nid]
            if rec['status']=='DECIDED_DELEGATED':
                rec['status']='RATIFIED_IN_PHASE';rec['phase_acceptance_id']=phase_id
                rec['authority']['acceptance_ref']=r['message_ref']
        phase.update(status='ACCEPTED',acceptance=r)
        if packet.get('inventory_hash'):
            work['inventory_confirmation']={'kind':'phase','phase_id':phase_id,'inventory_hash':ip['hash'],'receipt':copy.deepcopy(r)}
        gid=work.get('active_grant_id')
        if gid:work['grants'][gid]['status']='CONSUMED'
        work['active_grant_id']=None
        work['history'].append({'event':'phase_accepted','phase_id':phase_id,'receipt':r})
        state.clear();state.update(work)

    def reopen_phase(self,state,phase_id,reason,receipt):
        self.check_state(state);require(nonblank(reason),'REOPEN_REASON_REQUIRED')
        require(phase_id in state['phases'],'UNKNOWN_PHASE')
        phase=state['phases'][phase_id]
        require(phase['status'] in ('ACTIVE','BLOCKED','AWAITING_HUMAN','ACCEPTED','STALE'),'PHASE_CANNOT_REOPEN')
        r=human_receipt(receipt,digest({'phase_id':phase_id,'gate_packet_hash':phase.get('gate_packet_hash'),'reason':reason}),'reopen')
        affected={phase_id}
        while True:
            more={pid for pid,p in state['phases'].items() if set(p['dependency_ids'])&affected}
            if more<=affected:break
            affected|=more
        previous=copy.deepcopy(phase)
        self.revoke_delegation(state,'Phase reopened: '+reason)
        for pid in sorted(affected):
            current=state['phases'][pid]
            state['history'].append({'event':'phase_revision_retired','phase_id':pid,'previous':copy.deepcopy(current),'at':now()})
            for nid in current['node_instance_ids']:
                rec=state['records'].get(nid)
                if rec:
                    self.retain_record_context(state, nid)
                    state['history'].append({'event':'decision_retired_by_phase','node_id':nid,'record':copy.deepcopy(rec),'at':now()})
                    rec['status']='STALE'
            for key in ('packet','acceptance'):current.pop(key,None)
            current.update(status='STALE',gate_packet_hash=None,delivered=[],grant_id=None)
        state['active_phase_id']=phase_id
        state['history'].append({'event':'phase_reopened','phase_id':phase_id,'reason':reason,'previous':previous,'receipt':r,'at':now()})
        # Starting/revising requires a new scoped mandate, never reuse consumed one.
        return sorted(affected)

    def completion_children(self, state, node_id):
        node = self.node(node_id)
        if node['kind'] == 'decision':
            return [state['records'][node_id]['proposal']['selected']]
        return [edge['node']['id'] for edge in node['children']]

    @read_snapshot
    def complete(self,state,node_id):
        if node_id not in self.nodes or not self.record_current(state,node_id) or self.blocked(node_id):return False
        return all(self.complete(state, child) for child in self.completion_children(state, node_id))

    def invalidate(self,state,node_id,reason):
        require(nonblank(reason),'INVALIDATION_REASON_REQUIRED');self.node(node_id)
        impacted={node_id};changed=True
        while changed:
            changed=False
            for nid,n in self.nodes.items():
                if nid not in impacted and (self.parents.get(nid) in impacted or bool(set(n.get('requires',[]))&impacted)):
                    impacted.add(nid);changed=True
        for nid in impacted:
            if nid in state['records']:state['records'][nid]['status']='STALE'
            k=self.nodes[nid].get('candidate_key')
            if k:state['candidates'].pop(k,None)
        for pid,phase in state.get('phases',{}).items():
            if set(phase['node_instance_ids']) & impacted and phase.get('status') in ('AWAITING_HUMAN','ACCEPTED'):
                phase['status']='STALE'  # Keep the old packet/hash for historical inspection.
        state['history'].append({'event':'invalidate','node_id':node_id,'reason':reason,'affected':sorted(impacted),'at':now()})
        return sorted(impacted)

    def validate_inventory(self,state,rows):
        require(isinstance(rows,list) and len(rows)==len(self.inventory) and all(isinstance(r,dict) for r in rows) and {r.get('skill_id') for r in rows}==set(self.inventory),'INVENTORY_COVERAGE_REQUIRED')
        refs = set()
        for row in rows:
            require(row.get('disposition') in ('APPLICABLE','NOT_APPLICABLE','DEFERRED','GOVERNANCE_ONLY') and nonblank(row.get('reason')),'INVENTORY_REASON_REQUIRED')
            row_refs = row.get('evidence_refs')
            require(isinstance(row_refs, list) and row_refs and all(nonblank(ref) for ref in row_refs), 'EVIDENCE_REFERENCE_REQUIRED')
            refs.update(row_refs)
        return [{**item, 'note': 'Inventory disposition evidence'} for item in self.resolve_refs(state, sorted(refs))]

    def inventory_hash_for(self, state, rows, evidence=None):
        if evidence is None:
            evidence = self.validate_inventory(state, rows)
        return digest({'baseline': self.inventory_hash, 'rows': rows,
                       'context': self.scope_hash(state), 'evidence': evidence})

    def checked_inventory_hash(self, state, proposal):
        evidence = self.validate_inventory(state, proposal['rows'])
        require(evidence == proposal['evidence'], 'INVENTORY_EVIDENCE_CHANGED')
        expected = self.inventory_hash_for(state, proposal['rows'], evidence)
        require(proposal['hash'] == expected, 'INVENTORY_CHANGED')
        return expected

    def propose_inventory(self,state,rows):
        self.check_state(state);evidence=self.validate_inventory(state,rows)
        self.bind_evidence_paths(state, evidence)
        h=self.inventory_hash_for(state,rows,evidence)
        state['inventory_proposal']={'hash':h,'rows':copy.deepcopy(rows),'evidence':evidence};state['inventory_confirmation']=None
        return h

    def confirm_inventory(self,state,receipt):
        p=state.get('inventory_proposal');require(p is not None,'INVENTORY_PROPOSAL_REQUIRED')
        expected = self.checked_inventory_hash(state, p)
        state['inventory_confirmation']=human_receipt(receipt,expected,'inventory')

    @read_snapshot
    def inventory_confirmed(self,state):
        p=state.get('inventory_proposal');r=state.get('inventory_confirmation')
        if not p or not r:return False
        try:
            expected = self.checked_inventory_hash(state, p)
            if r.get('kind')=='phase':
                phase=state['phases'][r['phase_id']]
                require(r['inventory_hash']==expected and phase['packet']['inventory_hash']==expected,'INVENTORY_CHANGED')
                human_receipt(r.get('receipt'),phase['gate_packet_hash'],'phase')
                require(self.phase_current(state,r['phase_id']),'PHASE_STALE')
            else:human_receipt(r,expected,'inventory')
            return True
        except (GateError,KeyError,ValueError,TypeError,OSError):return False

    @read_snapshot
    def status(self,state):
        act=self.active(state);f=self.frontier(state);ic=self.inventory_confirmed(state)
        deferred=[]
        if ic:
            deferred=[r['skill_id'] for r in state['inventory_proposal']['rows'] if r['disposition']=='DEFERRED']
        applied={r['skill_id'] for nid in act if self.record_current(state,nid)
                 for r in state['records'][nid]['proposal']['skill_reviews'] if r['status']=='APPLIED'}
        unreviewed=[];conflicts=[]
        if ic:
            for row in state['inventory_proposal']['rows']:
                if row['disposition']=='APPLICABLE' and row['skill_id'] not in applied:
                    unreviewed.append(row['skill_id'])
                if row['disposition']=='NOT_APPLICABLE' and row['skill_id'] in applied:
                    conflicts.append(row['skill_id'])
        unresolved=[nid for nid in act if self.blocked(nid)]
        not_verified=[];failed_checks=[];unknown_checks=[]
        for nid in act:
            rec=state['records'].get(nid)
            if not rec:continue
            if rec.get('proposal',{}).get('verification')=='NOT_VERIFIED':not_verified.append(nid)
            try:
                ch=self.check_outcomes(state,nid,rec['proposal'])
                if ch['unverified_ids'] or ch['unknown_applicability_ids']:not_verified.append(nid)
                if ch['blocking_ids']:failed_checks.append(nid)
                if ch['unknown_applicability_ids']:unknown_checks.extend(ch['unknown_applicability_ids'])
            except (GateError,KeyError,TypeError,ValueError,OSError):
                failed_checks.append(nid)
        not_verified=sorted(set(not_verified));failed_checks=sorted(set(failed_checks))
        return {'project_id':state['project_id'],'tree_version':self.tree['version'],'revision':state['revision'],
            'frontier':f,'active_node_count':len(act),'approved_current_count':sum(self.record_current(state,i) for i in act),
            'inventory_confirmed':ic,'inventory_pending':[] if ic else list(self.inventory),
            'deferred_skills':deferred,'unreviewed_applicable_skills':unreviewed,'inventory_conflicts':conflicts,'blocked_nodes':unresolved,'unverified_nodes':not_verified,'failed_required_check_nodes':failed_checks,'unknown_applicability_checks':sorted(set(unknown_checks)),
            'assistance_level':state.get('assistance_level','manual'),'active_phase_id':state.get('active_phase_id'),
            'phase_statuses':{pid:p['status'] for pid,p in state.get('phases',{}).items()},
            'delegated_pending':sum(r.get('status')=='DECIDED_DELEGATED' for r in state['records'].values()),
            'ready_for_human_handoff':bool(state.get('phase_map')) and all(self.phase_current(state,pid) for pid,p in state.get('phases',{}).items() if any(nid in act for nid in p['node_instance_ids'])) and self.complete(state,'Q00') and ic and not deferred and not unreviewed and not conflicts and not unresolved and not not_verified and not failed_checks,
            'permission_to_execute':False,'external_tool_enforcement':False,'authenticated_human_identity':False,
            'limitations':['Supervised pilot; receipt contents are not authenticated.',
                           'Source bytes received do not prove reading or correct use.',
                           'One atomic component requirement per session; use a separate named session for another requirement.',
                           'No server or automatic cross-chat/cloud persistence. Export and explicitly save the ledger.',
                           'Original tree has incomplete and contextual criteria; no universal coverage claim.']}


def load_state(path, allow_legacy=False):
    p=Path(path);require(p.is_file() and not p.is_symlink(),'STATE_MISSING_OR_SYMLINK')
    s=json.loads(p.read_text())
    require(isinstance(s,dict),'STATE_OBJECT_REQUIRED')
    claimed=s.pop('integrity',None)
    require(claimed==digest(s),'STATE_INTEGRITY_MISMATCH')
    require(s.get('schema')==SCHEMA or (allow_legacy and s.get('schema')==LEGACY_SCHEMA),'STATE_SCHEMA_MISMATCH_USE_UPGRADE_STATE')
    return s


def context_command(path, command, *, node_id=None, query=None, proposal=None, expected_revision=None):
    path = Path(path)
    require(not path.resolve().is_relative_to(SKILL_DIR.parent.parent.resolve()), 'STATE_MUST_BE_OUTSIDE_PLUGIN')
    router = Router()
    state = load_state(path)
    router.check_state(state)
    revision = state['revision']
    if command == 'next':
        return router.context_next(state)
    if command == 'propose':
        require(router.context_required(state, node_id), 'CONTEXT_NODE_OUTSIDE_PILOT')
        require(expected_revision == revision, 'STATE_REVISION_CONFLICT')
        proposal_hash = router.propose(state, node_id, proposal)
        return {'proposal_hash': proposal_hash, 'state': 'AWAITING_HUMAN',
                'revision': save_state(path, state, revision)}
    previous = state.get('context_packets', {}).get(node_id)
    result = router.open_context(state, node_id, path.with_name(path.name+'.context.sqlite3'), query=query)
    if query is None and previous != state['context_packets'][node_id]:
        revision = save_state(path, state, revision)
    return {**result, 'revision': revision}


def save_state(path,state,expected_revision):
    p=Path(path);p.parent.mkdir(parents=True,exist_ok=True)
    require(not p.is_symlink(),'STATE_SYMLINK_FORBIDDEN')
    lock=p.with_suffix(p.suffix+'.lock')
    try:fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    except FileExistsError:raise GateError('STATE_BUSY_RETRY_AFTER_OWNER_FINISHES')
    temp=None
    try:
        os.close(fd)
        if p.exists():
            require(expected_revision is not None,'STATE_ALREADY_EXISTS')
            current=load_state(p)
            require(current['revision']==expected_revision,'STATE_REVISION_CONFLICT')
            next_revision=current['revision']+1
        else:
            require(expected_revision is None,'STATE_MISSING_REVISION_CONFLICT');next_revision=0
        out=copy.deepcopy(state);out.pop('integrity',None);out['revision']=next_revision
        out['integrity']=digest(out)
        tf=tempfile.NamedTemporaryFile('w',encoding='utf-8',dir=p.parent,delete=False);temp=Path(tf.name)
        with tf:
            json.dump(out,tf,ensure_ascii=False,indent=2,allow_nan=False);tf.write('\n');tf.flush();os.fsync(tf.fileno())
        os.replace(temp,p);temp=None
        return next_revision
    finally:
        if temp and temp.exists():temp.unlink()
        lock.unlink(missing_ok=True)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state',type=Path,help='Project-owned portable ledger, outside plugin directory')
    sub=parser.add_subparsers(dest='cmd',required=True)
    def command(name, summary, description=None):
        return sub.add_parser(name, help=summary, description=description or summary)

    p = command('init', 'Create a new project ledger.')
    p.add_argument('--project-id', required=True)
    p.add_argument('--scope', required=True)
    p.add_argument('--mode', choices=['design', 'audit'], default='design')
    p.add_argument('--medium', default='web')
    p.add_argument('--context-pilot', action='store_true', help='Require a source and capture packet for the G5 audit node.')
    command('status', 'Show the ledger revision, open decisions and outstanding checks.')
    command('verify-package', 'Verify the tree baseline and report inventory and node counts.')
    command('phase-template', 'Print the default phase map and its target hash.')
    p = command('upgrade-state', 'Migrate a portable 0.1 or 0.2 bundle to a new 0.3 bundle.')
    p.add_argument('--bundle', type=Path, required=True)
    p.add_argument('--output', type=Path)
    p.add_argument('--dry-run', action='store_true', help='Show the migration report without writing a bundle.')

    p = command('configure', 'Record a phase map with its confirmation receipt.')
    p.add_argument('--file', type=Path, required=True, help='JSON object containing phase_map and receipt.')
    for name, summary in (
        ('structure-set', 'Record confirmation of a set of node structures.'),
        ('grant', 'Register a delegation grant with its receipt.'),
        ('grant-packet', 'Calculate the target hash of a proposed grant.'),
    ):
        p = command(name, summary)
        p.add_argument('--file', type=Path, required=True)

    p = command('structure-manifest', 'List node IDs and their combined structure hash.')
    p.add_argument('--nodes', nargs='+', default=['ALL'])
    p = command('grant-template', 'Generate a proposed delegation grant for a phase.')
    p.add_argument('phase_id')
    p.add_argument('--level', choices=['manual', 'guided', 'phase_auto'], default='manual')
    p = command('delegate', 'Record a node decision under an active delegation grant.')
    p.add_argument('node_id')
    for name, summary in (
        ('phase-prepare', 'Prepare a phase and its deliverables for human acceptance.'),
        ('phase-accept', 'Record human acceptance of a prepared phase.'),
    ):
        p = command(name, summary)
        p.add_argument('phase_id')
        p.add_argument('--file', type=Path, required=True)
    p = command('phase-reopen', 'Reopen a phase using a reason and a receipt.')
    p.add_argument('phase_id')
    p.add_argument('--reason', required=True)
    p.add_argument('--file', type=Path, required=True)
    p = command('revoke', 'Revoke active delegation and return to manual operation.')
    p.add_argument('--reason', required=True)
    p = command('fact', 'Record a project fact and update affected decisions.')
    p.add_argument('fact_id')
    p.add_argument('--file', type=Path, required=True)
    p = command('resume', 'Restore a portable 0.3 bundle into a new ledger.')
    p.add_argument('--bundle', type=Path, required=True)
    p = command('node', 'Show the decision packet for a node.')
    p.add_argument('node_id')
    command('context-next', 'Show pending nodes in the current project and phase.')
    p = command('context-open', 'Prepare the required source sections for the G5 pilot node.')
    p.add_argument('node_id')
    p = command('context-search', 'Search optional source sections in the G5 pilot node.')
    p.add_argument('node_id')
    p.add_argument('--query', required=True)
    p = command('source', 'Register the bytes and provenance of a skill source.')
    for flag in ('--skill', '--file', '--commit', '--git-blob', '--source-ref'):
        p.add_argument(flag, required=True)
    for name, summary in (
        ('structure', 'Record confirmation of one node structure.'),
        ('propose', 'Submit a node decision for review.'),
        ('confirm', 'Record human confirmation of a proposed node decision.'),
    ):
        p = command(name, summary)
        p.add_argument('node_id')
        p.add_argument('--file', type=Path, required=True)
    p = command('invalidate', 'Mark a decision and its dependents stale.')
    p.add_argument('node_id')
    p.add_argument('--reason', required=True)
    p = command('inventory', 'List the skill catalog or record an inventory proposal.',
                description='Without --file, list the skill catalog. With --file, record a proposal for human review.')
    p.add_argument('--file', type=Path, metavar='PROPOSAL.json',
                   help='JSON array with one entry per skill. Each entry requires '
                        'skill_id, disposition, reason and evidence_refs.')
    p = command('confirm-inventory', 'Record human confirmation of inventory dispositions.')
    p.add_argument('--file', type=Path, required=True)
    p = command('export', 'Write a new portable bundle with the ledger and its evidence.')
    p.add_argument('--output', type=Path, required=True)
    a=parser.parse_args(argv)
    if a.cmd.startswith('context-'):
        require(a.state is not None, 'STATE_PATH_REQUIRED')
        return context_command(a.state, a.cmd.removeprefix('context-'),
                               node_id=getattr(a, 'node_id', None), query=getattr(a, 'query', None))
    router=Router()
    if a.cmd=='verify-package':return {'baseline_verified':router.verify_baseline(),'inventory_count':len(router.inventory),'expanded_nodes':len(router.nodes)}
    if a.cmd=='phase-template':return {'phase_map':router.default_phase_map(),'target_hash':digest(router.default_phase_map()),'kind':'phase_map'}
    if a.cmd=='structure-manifest':
        ids=list(router.nodes) if a.nodes==['ALL'] else a.nodes
        return {'node_ids':ids,'target_hash':router.structure_set_hash(ids),'kind':'structure_set'}
    if a.cmd=='upgrade-state':
        from migration import upgrade_bundle
        if a.output is not None:require(not a.output.resolve().is_relative_to(SKILL_DIR.parent.parent.resolve()),'OUTPUT_MUST_BE_OUTSIDE_PLUGIN')
        return upgrade_bundle(router,a.bundle,a.output,a.dry_run)
    require(a.state is not None,'STATE_PATH_REQUIRED')
    require(not a.state.resolve().is_relative_to(SKILL_DIR.parent.parent.resolve()),'STATE_MUST_BE_OUTSIDE_PLUGIN')
    if a.cmd=='init':
        state=router.new_state(a.project_id,a.medium,a.mode,a.scope,context_pilot=a.context_pilot)
        save_state(a.state,state,None);return router.status(state)
    if a.cmd=='resume':
        from migration import inspect_portable_bundle
        info=inspect_portable_bundle(a.bundle);state=info['state'];router.check_state(state)
        state['artifact_paths']=info['paths']
        if state.get('active_grant_id'):router.revoke_delegation(state,'Resumed in another context; explicit delegation must be renewed')
        state['assistance_level']='manual'
        state['history'].append({'event':'resumed','at':now(),'scope':'Paths relocated; no autonomy increase'})
        save_state(a.state,state,None)
        return router.status(state)
    state=load_state(a.state);router.check_state(state);rev=state['revision'];changed=True
    payload=json.loads(a.file.read_text()) if getattr(a,'file',None) and a.cmd!='source' else None
    if a.cmd=='status':return router.status(state)
    if a.cmd=='node':return router.packet(state,a.node_id)
    if a.cmd=='source':router.register_source(state,a.skill,a.file,a.commit,a.git_blob,a.source_ref);out={'source_registered':a.skill,'invoked':False}
    elif a.cmd=='structure':router.confirm_structure(state,a.node_id,payload);out={'node':a.node_id,'structure':'CONFIRMED','project_approval':False}
    elif a.cmd=='propose':out={'proposal_hash':router.propose(state,a.node_id,payload),'state':'AWAITING_HUMAN'}
    elif a.cmd=='confirm':router.confirm_decision(state,a.node_id,payload);out={'node':a.node_id,'recorded':'APPROVED','authentication':'OPERATOR_ASSERTED'}
    elif a.cmd=='invalidate':out={'invalidated':router.invalidate(state,a.node_id,a.reason)}
    elif a.cmd=='inventory':
        if a.file is None:return {'baseline':router.inventory_hash,'skills':list(router.inventory.values()),'approval':'NOT_IMPLIED'}
        out={'inventory_hash':router.propose_inventory(state,payload),'state':'AWAITING_HUMAN'}
    elif a.cmd=='confirm-inventory':router.confirm_inventory(state,payload);out={'inventory':'CONFIRMED','meaning':'Dispositions only; not blanket skill execution'}
    elif a.cmd=='export':
        from migration import export_bundle
        require(not a.output.resolve().is_relative_to(SKILL_DIR.parent.parent.resolve()),'EXPORT_MUST_BE_OUTSIDE_PLUGIN')
        return export_bundle(state,a.output)
    elif a.cmd=='configure':
        require(isinstance(payload, dict) and 'phase_map' in payload and 'receipt' in payload,
                'CONFIGURE_OBJECT_REQUIRED: expected phase_map and receipt')
        router.configure_phases(state,payload['phase_map'],payload['receipt']);out={'phase_map':'CONFIRMED','project_approval':False}
    elif a.cmd=='structure-set':
        router.confirm_structure_set(state,payload['node_ids'],payload['receipt']);out={'structure_set':'CONFIRMED','project_approval':False}
    elif a.cmd=='grant-template':
        grant=router.grant_template(state,a.phase_id,a.level)
        return {'grant':grant,'target_hash':router.grant_hash(state,grant),'kind':'delegation','note':'Replace message_ref/quote with the actual authorization, then use grant-packet --file to calculate the exact hash before registering.'}
    elif a.cmd=='grant-packet':
        require(not validate_assistance(payload,state['phase_map']),'ASSISTANCE_GRANT_INVALID')
        return {'grant':payload,'target_hash':router.grant_hash(state,payload),'kind':'delegation'}
    elif a.cmd=='grant':
        router.grant_assistance(state,payload['grant'],payload['receipt']);out={'grant':'ACTIVE','phase':state['active_phase_id'],'level':state['assistance_level']}
    elif a.cmd=='delegate':
        router.delegate_decision(state,a.node_id);out={'node':a.node_id,'status':'DECIDED_DELEGATED','human_accepted':False}
    elif a.cmd=='phase-prepare':out=router.prepare_phase(state,a.phase_id,payload)
    elif a.cmd=='phase-accept':
        router.accept_phase(state,a.phase_id,payload);out={'phase':a.phase_id,'status':'ACCEPTED','next_phase_authorized':False}
    elif a.cmd=='phase-reopen':
        router.reopen_phase(state,a.phase_id,a.reason,payload);out={'phase':a.phase_id,'status':state['phases'][a.phase_id]['status'],'delegation_required':True}
    elif a.cmd=='revoke':
        router.revoke_delegation(state,a.reason);out={'level':'manual','delegation':'REVOKED'}
    elif a.cmd=='fact':out={'invalidated':router.set_fact(state,a.fact_id,payload)}
    else:raise GateError('UNKNOWN_COMMAND')
    if changed:out['revision']=save_state(a.state,state,rev)
    return out

if __name__=='__main__':
    try: print(json.dumps(main(),ensure_ascii=False,indent=2))
    except (GateError,OSError,ValueError,KeyError,TypeError) as e:
        print(json.dumps({'status':'BLOCKED','error':str(e)},ensure_ascii=False),file=sys.stderr);sys.exit(2)
