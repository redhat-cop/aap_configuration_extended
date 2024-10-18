============================================
infra.aap_configuration_extended Release Notes
============================================

.. contents:: Topics


v0.1.0
======

Major Changes
-------------

- Adds Configuration as Code filetree_create - A role to export and convert all  Controller's objects configuration in yaml files to be consumed with previous roles.
- Adds Configuration as Code filetree_read role - A role to load controller variables (objects) from a hierarchical and scalable directory structure.
- Adds Configuration as Code object_diff role - A role to get differences between code and controller. It will give us the lists to remove absent objects in the controller which they are not in code.

Minor Changes
-------------

- Adds credential and organization options for schedule role.
- inventory_sources - update ``source_vars`` to parse Jinja variables using the same workaround as inventories role.
