# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Discover nested Workflow Job Templates and Job Templates from a seed WFJT."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = """
name: workflow_related_graph
author: Ivan Aragonés (@ivarmu)
short_description: Walk nested Workflow Job Template nodes to discover related objects
description:
  - Starting from a Workflow Job Template name, follow nested workflow nodes until
    only Job Template (or approval) leaves remain.
  - Returns sorted lists of workflow names, job template names, and inventory names
    referenced on nodes.
  - Uses the same Automation Platform Gateway client as C(ansible.platform.gateway_api)
    so SSL and auth stay out of forked Ansible workers.
options:
  _terms:
    description:
      - Name of the seed Workflow Job Template.
    required: true
  max_objects:
    description:
      - Maximum objects returned per paginated API list request.
    type: int
    default: 1000
  max_workflows:
    description:
      - Safety cap on how many distinct Workflow Job Templates to visit.
    type: int
    default: 5000
extends_documentation_fragment: ansible.platform.auth_lookup
notes:
  - Object identity is by name (Configuration as Code); numeric IDs are not returned.
...
"""

EXAMPLES = """
- name: Discover nested workflows and job templates from MainWF
  ansible.builtin.set_fact:
    related_graph: >-
      {{ query(
           'infra.aap_configuration_extended.workflow_related_graph',
           'MainWF',
           host=aap_hostname,
           oauth_token=aap_token,
           verify_ssl=aap_validate_certs,
         ) | first }}

- name: Show discovered job templates
  ansible.builtin.debug:
    var: related_graph.job_templates
...
"""

RETURN = """
_raw:
  description:
    - One dict with keys C(workflows), C(job_templates), and C(inventories)
      (each a sorted list of names).
  type: list
  elements: dict
  returned: success
...
"""

from ansible.errors import AnsibleError
from ansible.module_utils._text import to_native
from ansible.plugins.lookup import LookupBase
from ansible.utils.display import Display


class LookupModule(LookupBase):
    """BFS walk of nested workflow_job_template nodes via ansible.platform API client."""

    display = Display()

    @staticmethod
    def _to_plain(value):
        """Strip Ansible tagged types for pickle/RPC boundaries."""
        import json

        if value is None:
            return None
        try:
            return json.loads(json.dumps(value))
        except (TypeError, ValueError):
            return str(value)

    @staticmethod
    def _token_string(oauth_token):
        """Normalize gateway token option (string or token module dict)."""
        token = LookupModule._to_plain(oauth_token)
        if token is None:
            return ""
        if isinstance(token, dict):
            return str(token.get("token") or token.get("oauth_token") or "")
        return str(token)

    def _build_gateway_config(self):
        from ansible_collections.ansible.platform.plugins.plugin_utils.platform.config import (
            GatewayConfig,
        )

        host = self._to_plain(self.get_option("host")) or "https://localhost/"
        return GatewayConfig(
            base_url=str(host),
            username=str(self._to_plain(self.get_option("username")) or ""),
            password=str(self._to_plain(self.get_option("password")) or ""),
            oauth_token=self._token_string(self.get_option("oauth_token")),
            verify_ssl=bool(self.get_option("verify_ssl")),
            request_timeout=float(self.get_option("request_timeout") or 60),
            connection_mode="direct",
        )

    @staticmethod
    def _results_list(payload):
        """Normalize search_api payload to a list of objects."""
        if payload is None:
            return []
        if isinstance(payload, list):
            return payload
        if isinstance(payload, dict):
            if "results" in payload:
                return payload.get("results") or []
            if "data" in payload:
                return payload.get("data") or []
            if payload.get("id") is not None or payload.get("name") is not None:
                return [payload]
        return []

    def _list_all(self, client, endpoint, query_params=None, max_objects=1000):
        data = client.search_api(
            endpoint=endpoint,
            query_params=query_params or {},
            return_all=True,
            max_objects=max_objects,
        )
        return self._results_list(data)

    def _walk_graph(self, client, seed_name, max_objects, max_workflows):
        workflows = set()
        job_templates = set()
        inventories = set()
        queue = [seed_name]
        seen = set()

        while queue and len(seen) < max_workflows:
            name = queue.pop(0)
            if not name or name in seen:
                continue
            seen.add(name)
            workflows.add(name)

            matches = self._list_all(
                client,
                "api/controller/v2/workflow_job_templates/",
                query_params={"name": name},
                max_objects=max_objects,
            )
            if not matches:
                self.display.vv("workflow_related_graph: no WFJT named %r" % (name,))
                continue

            wf = matches[0]
            related = wf.get("related") or {}
            nodes_url = related.get("workflow_nodes")
            if not nodes_url:
                continue

            nodes = self._list_all(client, nodes_url, max_objects=max_objects)
            for node in nodes:
                summary = node.get("summary_fields") or {}
                inv = summary.get("inventory") or {}
                if inv.get("name"):
                    inventories.add(inv["name"])

                ujt = summary.get("unified_job_template") or {}
                ujt_name = ujt.get("name")
                ujt_type = ujt.get("unified_job_type")
                if not ujt_name:
                    continue
                if ujt_type == "job":
                    job_templates.add(ujt_name)
                elif ujt_type == "workflow_job" and ujt_name not in seen:
                    queue.append(ujt_name)

        if len(seen) >= max_workflows and queue:
            raise AnsibleError("workflow_related_graph: exceeded max_workflows=%s while walking from %r" % (max_workflows, seed_name))

        return {
            "workflows": sorted(workflows),
            "job_templates": sorted(job_templates),
            "inventories": sorted(inventories),
        }

    def run(self, terms, variables=None, **kwargs):
        if not terms:
            raise AnsibleError("workflow_related_graph requires a seed Workflow Job Template name")
        if len(terms) != 1:
            raise AnsibleError("workflow_related_graph accepts exactly one seed name")

        self.set_options(direct=kwargs)
        seed_name = str(self._to_plain(terms[0]) or "").strip()
        if not seed_name:
            raise AnsibleError("workflow_related_graph seed name must not be empty")

        max_objects = int(self.get_option("max_objects") or 1000)
        max_workflows = int(self.get_option("max_workflows") or 5000)

        try:
            from ansible_collections.ansible.platform.plugins.plugin_utils.manager.process_manager import (
                spawn_ephemeral_client,
            )

            gateway_config = self._build_gateway_config()
            client, _facts = spawn_ephemeral_client({}, gateway_config)
        except Exception as exc:
            raise AnsibleError("workflow_related_graph: failed to connect to platform manager: {0}".format(to_native(exc)))

        try:
            graph = self._walk_graph(client, seed_name, max_objects, max_workflows)
        except AnsibleError:
            raise
        except Exception as exc:
            raise AnsibleError("workflow_related_graph: failed walking from {0!r}: {1}".format(seed_name, to_native(exc)))
        finally:
            try:
                client.shutdown_manager()
            except Exception:
                pass

        return [graph]
