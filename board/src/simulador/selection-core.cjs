'use strict';

function selectProfile(route, scope, functionId, profiles) {
  if (route === 'auditoria') return profiles.auditoria;
  if (scope === 'function' && functionId === 'type-choice') return profiles['solo-fuente'];
  if (scope === 'function' && functionId === 'type-micro') return profiles['solo-micro'];
  return profiles[route] || profiles.tipografia;
}

function assessDomains({ route, domain, domainRequired, functionRequired, owners, domains, reviews, blocked, unresolved }) {
  const errors = [];
  const pendingDomains = [];
  const assessments = {};
  const counts = { applies: 0, pending: 0, notApplicable: 0 };

  if (functionRequired) {
    errors.push({
      code: 'FUNCTION_REQUIRED',
      message: 'Falta seleccionar una función.'
    });
  }
  if (domainRequired && !domain) {
    errors.push({
      code: route === 'auditoria' ? 'AUDIT_DOMAIN_REQUIRED' : 'DOMAIN_REQUIRED',
      message: route === 'auditoria'
        ? 'Falta delimitar el dominio de la auditoría.'
        : 'Falta delimitar el dominio de la selección.'
    });
  }
  if (route === 'auditoria' && domain && !owners.length && !functionRequired) {
    errors.push({
      code: 'AUDIT_FUNCTION_OUTSIDE_DOMAIN',
      message: 'La función seleccionada queda fuera del dominio de auditoría.'
    });
  }
  if (blocked.length) {
    errors.push({
      code: 'FUNCTION_NOT_PROPOSABLE', function_ids: blocked,
      message: 'La selección incluye una función excluida o sin modelar.'
    });
  }
  if (unresolved.length && !(domainRequired && !domain)) {
    errors.push({
      code: 'REQUIRED_OWNER_PENDING', function_ids: unresolved,
      message: 'Falta delimitar un especialista para una función de la selección.'
    });
  }

  for (const owner of domains) {
    const expected = owners.includes(owner);
    const record = reviews[owner];
    const applicability = record?.status || (expected ? 'applies' : 'pending');
    const reason = record?.reason || '';
    assessments[owner] = { applicability, reason, reviewed: false, verified: false, approved: false };

    if (applicability === 'pending') {
      counts.pending++;
      pendingDomains.push(owner);
    }
    if (applicability === 'applies') counts.applies++;
    if (applicability !== 'not_applicable') continue;

    const justified = Boolean(reason.trim());
    if (expected) {
      errors.push({
        code: 'REQUIRED_DOMAIN_NOT_APPLICABLE', domain: owner,
        message: 'Contradicción: el dominio pertenece a la ruta propuesta.'
      });
    }
    if (!justified) {
      errors.push({
        code: 'MISSING_JUSTIFICATION', domain: owner,
        message: 'Falta justificar por qué no aplica.'
      });
    }
    if (!expected && justified) counts.notApplicable++;
  }

  return {
    assessments,
    counts,
    validation: { valid: errors.length === 0, errors },
    completeness: {
      complete: pendingDomains.length === 0 && unresolved.length === 0 && !functionRequired && (!domainRequired || Boolean(domain)),
      pending_domains: pendingDomains
    }
  };
}

function resolveSelection(input, { catalog, policy }) {
  const { route = 'tipografia', scope = 'function', permit = 'read', reviews = {} } = input;
  const routeFunctions = catalog.routes.find(entry => entry.id === route)?.functions || [];
  const hasExplicitFunction = Object.prototype.hasOwnProperty.call(input, 'functionId') && input.functionId !== undefined;
  const functionId = hasExplicitFunction
    ? (input.functionId || '')
    : (routeFunctions[0] || 'type-choice');
  const requestedFunctions = scope === 'function' ? (functionId ? [functionId] : []) : [...routeFunctions];
  const functionRequired = scope === 'function' && requestedFunctions.length === 0;
  const functionsById = new Map(catalog.functions.map(entry => [entry.id, entry]));
  const functionOwners = id => functionsById.get(id)?.owners || [];
  const isBlocked = id => policy.special_blocked.includes(id);
  const auditRoute = route === 'auditoria';

  function auditOwner(id, domain) {
    if (!policy.reviewable_domains.includes(domain) || !routeFunctions.includes(id)) return null;
    // Visual QA delegates to the affected design domain, including family selection in G2.
    const allowed = policy.audit_domain_overrides[id] || functionOwners(id);
    return allowed.includes(domain) ? domain : null;
  }

  function resolveOwner(id, domain) {
    if (isBlocked(id)) return null;
    if (auditRoute) return auditOwner(id, domain);
    if (domain && (id === 'accessibility' || functionOwners(id).includes(domain))) return domain;
    return policy.owner_by_function[id] || policy.default_context_owner[route]?.[id] || null;
  }

  const ambiguous = requestedFunctions.some(id => !resolveOwner(id, '') && !isBlocked(id));
  const multipleOwners = requestedFunctions.some(id => functionOwners(id).length > 1 && !policy.owner_by_function[id]);
  const showDomain = auditRoute || ambiguous || multipleOwners;
  let domainOptions = [];
  if (showDomain) {
    domainOptions = auditRoute || requestedFunctions.includes('accessibility')
      ? [...policy.reviewable_domains]
      : [...new Set(requestedFunctions.flatMap(functionOwners).filter(owner => /^G[1-7]$/.test(owner)))];
  }
  const domain = domainOptions.includes(input.domain) ? input.domain : '';
  const selectedFunctions = auditRoute
    ? requestedFunctions.filter(id => isBlocked(id) || auditOwner(id, domain))
    : [...requestedFunctions];
  const owners = [...new Set(selectedFunctions.map(id => resolveOwner(id, domain)).filter(Boolean))];
  const domainRequired = auditRoute || (!owners.length && showDomain);
  const blocked = requestedFunctions.filter(isBlocked);
  const unresolved = auditRoute ? [] : requestedFunctions.filter(id => !isBlocked(id) && !resolveOwner(id, domain));
  const profile = selectProfile(route, scope, functionId, policy.profiles);
  const audit = auditRoute || /^Audit\b/.test(profile.mode);

  const contributions = catalog.skills.flatMap(skill => skill.contributions
    .filter(item => selectedFunctions.includes(item.function_id))
    .map(item => ({ ...item, skill })));
  const isWrite = item => policy.writes.includes(item.effect);
  const support = {
    read: contributions.filter(item => !isWrite(item) && item.effect !== 'externo' && item.effect !== 'excluir'),
    write: contributions.filter(isWrite)
  };
  const nodesByFunction = Object.fromEntries(selectedFunctions.map(id => [id, [...(functionsById.get(id)?.nodes || [])]]));

  return {
    requestedFunctions,
    selectedFunctions,
    owners,
    domain,
    domainOptions,
    showDomain,
    domainRequired,
    permit: audit ? 'read' : permit,
    audit,
    profile,
    support,
    nodesByFunction,
    ...assessDomains({ route, domain, domainRequired, functionRequired, owners, domains: policy.reviewable_domains, reviews, blocked, unresolved })
  };
}

module.exports = { resolveSelection };
