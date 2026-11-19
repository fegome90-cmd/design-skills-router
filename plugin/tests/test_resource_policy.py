import unittest,sys,copy
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'skills/design-tree/scripts'))
from runner import Router
from contracts import policy_hash
class ResourcePolicyTests(unittest.TestCase):
 def test_changed_resource_pin_changes_related_policy_only(self):
  r=Router();before=policy_hash(r.nodes['QA01'],r.rules,r.contracts);root=policy_hash(r.nodes['Q00'],r.rules,r.contracts)
  changed=copy.deepcopy(r.contracts);changed['resources'][0]['git_blob']='0'*40
  self.assertNotEqual(before,policy_hash(r.nodes['QA01'],r.rules,changed))
  self.assertEqual(root,policy_hash(r.nodes['Q00'],r.rules,changed))
