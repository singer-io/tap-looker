# tap-looker

This is a [Singer](https://singer.io) tap that produces JSON-formatted data
following the [Singer
spec](https://github.com/singer-io/getting-started/blob/master/SPEC.md).

This tap:

- Pulls raw data from the [Looker v4.0 API](https://developers.looker.com/api/explorer/4.0)
- Extracts the following endpoint **streams**:
  - [color_collections](https://developers.looker.com/api/explorer/4.0/methods/ColorCollection/all_color_collections)
  - [connections](https://developers.looker.com/api/explorer/4.0/methods/Connection/all_connections)
  - [content_metadata](https://developers.looker.com/api/explorer/4.0/methods/Content/all_content_metadatas)
  - [content_metadata_access](https://developers.looker.com/api/explorer/4.0/methods/Content/all_content_metadata_accesses)
  - [dashboards](https://developers.looker.com/api/explorer/4.0/methods/Dashboard/all_dashboards)
    - [dashboard_elements](https://developers.looker.com/api/explorer/4.0/methods/Dashboard/dashboard_dashboard_elements)
    - [dashboard_filters](https://developers.looker.com/api/explorer/4.0/methods/Dashboard/dashboard_dashboard_filters)
    - [dashboard_layouts](https://developers.looker.com/api/explorer/4.0/methods/Dashboard/dashboard_dashboard_layouts)
  - [datagroups](https://developers.looker.com/api/explorer/4.0/methods/Datagroup/all_datagroups)
  - [folders](https://developers.looker.com/api/explorer/4.0/methods/Folder/all_folders)
  - [groups](https://developers.looker.com/api/explorer/4.0/methods/Group/all_groups)
  - [integration_hubs](https://developers.looker.com/api/explorer/4.0/methods/Integration/all_integration_hubs)
  - [integrations](https://developers.looker.com/api/explorer/4.0/methods/Integration/all_integrations)
  - [lookml_dashboards](https://developers.looker.com/api/explorer/4.0/methods/Dashboard/all_dashboards)
  - [lookml_models](https://developers.looker.com/api/explorer/4.0/methods/LookmlModel/all_lookml_models)
    - [models](https://developers.looker.com/api/explorer/4.0/methods/LookmlModel/lookml_model)
    - [explores](https://developers.looker.com/api/explorer/4.0/methods/LookmlModel/lookml_model_explore)
  - [looks](https://developers.looker.com/api/explorer/4.0/methods/Look/all_looks)
  - [projects](https://developers.looker.com/api/explorer/4.0/methods/Project/all_projects)
    - [git_branches](https://developers.looker.com/api/explorer/4.0/methods/Project/all_git_branches)
    - [project_files](https://developers.looker.com/api/explorer/4.0/methods/Project/all_project_files)
  - [queries](https://developers.looker.com/api/explorer/4.0/methods/Query/query)
    - [merge_queries](https://developers.looker.com/api/explorer/4.0/methods/Query/merge_query)
    - [query_history](https://developers.looker.com/api/explorer/4.0/methods/Query) (POST)
  - [roles](https://developers.looker.com/api/explorer/4.0/methods/Role/all_roles)
    - [model_sets](https://developers.looker.com/api/explorer/4.0/methods/Role/all_model_sets)
    - [permission_sets](https://developers.looker.com/api/explorer/4.0/methods/Role/all_permission_sets)
    - [permissions](https://developers.looker.com/api/explorer/4.0/methods/Role/all_permissions)
    - [role_groups](https://developers.looker.com/api/explorer/4.0/methods/Role/role_groups)
  - [scheduled_plans](https://developers.looker.com/api/explorer/4.0/methods/ScheduledPlan/all_scheduled_plans)
    - [for dashboards](https://developers.looker.com/api/explorer/4.0/methods/ScheduledPlan/scheduled_plans_for_dashboard)
    - [for lookml_dashboards](https://developers.looker.com/api/explorer/4.0/methods/ScheduledPlan/scheduled_plans_for_lookml_dashboard)
    - [for looks](https://developers.looker.com/api/explorer/4.0/methods/ScheduledPlan/scheduled_plans_for_look)
  - [themes](https://developers.looker.com/api/explorer/4.0/methods/Theme/all_themes)
  - [user_attributes](https://developers.looker.com/api/explorer/4.0/methods/UserAttribute/all_user_attributes)
    - [user_attribute_group_value](https://developers.looker.com/api/explorer/4.0/methods/UserAttribute/all_user_attribute_group_values)
  - [user_login_lockouts](https://developers.looker.com/api/explorer/4.0/methods/Auth/all_user_login_lockouts)
  - [users](https://developers.looker.com/api/explorer/4.0/methods/User/all_users)
    - [user_attribute_values](https://developers.looker.com/api/explorer/4.0/methods/User/user_attribute_user_values)
    - [user_sessions](https://developers.looker.com/api/explorer/4.0/methods/User/all_user_sessions)
  - [versions](https://developers.looker.com/api/explorer/4.0/methods/Config/versions)
  - [workspaces](https://developers.looker.com/api/explorer/4.0/methods/Workspace/workspace)

- All endpoints replicate FULL_TABLE (ALL records, every time). Currently, the Looker API does not support paginating, sorting, filtering, or providing audit fields (like created/modified datetimes).
- Primary Key field(s): Almost all endpoint have an `id` primary key
  - lookml_models, models, git_branches use a combination key of `name` and `project_name`
  - git_branches use a combination key of `name` and `project_id`
  - project_files use `id` and `project_id`
  - connections use `name`
  - user_attribute_values use `user_id` and `user_attribute_id`
  - group_attribute_values use `group_id` and `attribute_value_id`
- Transformations: Remove `can` nodes; IDs to string; fix JSON validation errors (datatypes)
- ALL JSON schema generated from Looker API Swagger Definitions


## Quick Start

1. Install

    Clone this repository, and then install using setup.py. We recommend using a virtualenv:

    ```bash
    > virtualenv -p python3 venv
    > source venv/bin/activate
    > python setup.py install
    OR
    > cd .../tap-looker
    > pip install .
    ```
2. Dependent libraries
    The following dependent libraries were installed.
    ```bash
    > pip install singer-python
    > pip install singer-tools
    > pip install target-stitch
    > pip install target-json

    ```
    - [singer-tools](https://github.com/singer-io/singer-tools)
    - [target-stitch](https://github.com/singer-io/target-stitch)

3. Create your tap's `config.json` file.
    - `subdomain` is the eading part of Looker URL before .looker.com; https://`bytecode`.looker.com
    - `client_id` and `client_secret` are your [API3 Keys](https://docs.looker.com/admin-options/settings/users#api3_keys), which may be generated and provided by a Looker Admin.
    - `domain` is usually `looker.com`, unless you have your own white-labeled URL.
    - `api_port` is usually `19999`, unless you are hosting Looker internally and are using a different port for the API.
    - `start_data` is not currently used. The Looker API does not provide audit dates or allow query filtering, sorting, and paging.
    - `user_agent` is used to identify yourself in the API logs.

    ```json
    {
        "subdomain": "YOUR_SUBDOMAIN",
        "client_id": "YOUR_LOOKER_CLIENT_ID",
        "client_secret": "YOUR_LOOKER_CLIENT_SECRET",
        "domain": "looker.com",
        "api_port": "19999",
        "start_date": "2019-01-01T00:00:00Z",
        "user_agent": "tap-looker <api_user_email@your_company.com>"
    }
    ```

4. Run the Tap in Discovery Mode
    This creates a catalog.json for selecting objects/fields to integrate:
    ```bash
    tap-looker --config config.json --discover > catalog.json
    ```
   See the Singer docs on discovery mode
   [here](https://github.com/singer-io/getting-started/blob/master/docs/DISCOVERY_MODE.md#discovery-mode).

5. Run the Tap in Sync Mode (with catalog) and [write out to state file](https://github.com/singer-io/getting-started/blob/master/docs/RUNNING_AND_DEVELOPING.md#running-a-singer-tap-with-a-singer-target)

    For Sync mode:
    ```bash
    > tap-looker --config tap_config.json --catalog catalog.json > state.json
    > tail -1 state.json > state.json.tmp && mv state.json.tmp state.json
    ```
    To load to json files to verify outputs:
    ```bash
    > tap-looker --config tap_config.json --catalog catalog.json | target-json > state.json
    > tail -1 state.json > state.json.tmp && mv state.json.tmp state.json
    ```
    To pseudo-load to [Stitch Import API](https://github.com/singer-io/target-stitch) with dry run:
    ```bash
    > tap-looker --config tap_config.json --catalog catalog.json | target-stitch --config target_config.json --dry-run > state.json
    > tail -1 state.json > state.json.tmp && mv state.json.tmp state.json
    ```

6. Test the Tap

    While developing the looker tap, the following utilities were run in accordance with Singer.io best practices:
    Pylint to improve [code quality](https://github.com/singer-io/getting-started/blob/master/docs/BEST_PRACTICES.md#code-quality):
    ```bash
    > pylint tap_looker -d missing-docstring -d logging-format-interpolation -d too-many-locals -d too-many-arguments
    ```
    Pylint test resulted in the following score:
    ```bash
    Your code has been rated at 9.73/10
    ```

    To [check the tap](https://github.com/singer-io/singer-tools#singer-check-tap) and verify working:
    ```bash
    > tap-looker --config tap_config.json --catalog catalog.json | singer-check-tap > state.json
    > tail -1 state.json > state.json.tmp && mv state.json.tmp state.json
    ```
    Check tap resulted in the following:
    ```bash
    The output is valid.
    It contained 3000 messages for 41 streams.

        155 schema messages
      2795 record messages
        50 state messages

    Details by stream:
    +-----------------------------+---------+---------+
    | stream                      | records | schemas |
    +-----------------------------+---------+---------+
    | datagroups                  | 19      | 1       |
    | lookml_dashboards           | 2       | 1       |
    | scheduled_plans             | 2       | 4       |
    | users                       | 62      | 1       |
    | user_attribute_values       | 1302    | 1       |
    | user_sessions               | 26      | 1       |
    | integration_hubs            | 1       | 1       |
    | workspaces                  | 2       | 1       |
    | integrations                | 24      | 1       |
    | themes                      | 2       | 1       |
    | roles                       | 8       | 1       |
    | role_groups                 | 3       | 1       |
    | dashboards                  | 44      | 1       |
    | dashboard_filters           | 20      | 1       |
    | content_metadata            | 183     | 5       |
    | dashboard_elements          | 131     | 1       |
    | merge_queries               | 1       | 44      |
    | queries                     | 155     | 46      |
    | dashboard_layouts           | 44      | 1       |
    | projects                    | 13      | 1       |
    | git_branches                | 166     | 1       |
    | project_files               | 151     | 1       |
    | user_attributes             | 17      | 1       |
    | user_attribute_group_values | 2       | 1       |
    | lookml_models               | 18      | 1       |
    | models                      | 18      | 1       |
    | explores                    | 25      | 18      |
    | looks                       | 69      | 1       |
    | color_collections           | 15      | 1       |
    | permissions                 | 40      | 1       |
    | permission_sets             | 9       | 1       |
    | content_metadata_access     | 106     | 3       |
    | model_sets                  | 9       | 1       |
    | versions                    | 1       | 1       |
    | user_login_lockouts         | 0       | 1       |
    | groups                      | 9       | 1       |
    | groups_in_group             | 10      | 1       |
    | connections                 | 14      | 1       |
    | folders                     | 35      | 1       |
    +-----------------------------+---------+---------+

    ```
---

Copyright &copy; 2019 Stitch
