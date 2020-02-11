import numbers
import hashlib
import singer

LOGGER = singer.get_logger()

# TRANSFORM JSON SCHEMAS: Looker Swagger to Singer.io JSON Schema
# Loop through and replace $ref references in nested dict and lists
def replace_refs(this_dict, swagger):
    for k, v in list(this_dict.items()):
        if k == 'properties' and isinstance(this_dict, dict):
            this_dict['additionalProperties'] = False
            this_dict['type'] = ['null', 'object']
        if isinstance(v, dict):
            is_nested_ref = False
            for key, val in list(v.items()):
                # If dict has nested $ref elements, replace those with the related swagger obj
                if key == '$ref':
                    is_nested_ref = True
                    obj = val.replace('#/definitions/', '')
                    new_v = replace_refs(swagger.get('definitions', {}).get(obj, {}), swagger)
            if is_nested_ref:
                # Replace parent node with nested reference node
                this_dict[k] = new_v
            replace_refs(v, swagger)
        elif isinstance(v, list):
            for i in list(v):
                if isinstance(i, dict):
                    replace_refs(i, swagger)
    return this_dict


# Convert type fields from single value to arrays, change IDs to strings,
# Also remove some Looker-specific JSON schema elements
def tranform_looker_schemas(this_dict):
    for k, v in list(this_dict.items()):
        # Convert ALL ID, Value, Count fields to Strings; solves Looker Swagger schema inconsistency
        #   IDs that can be EITHER integer or string (space_id, dashboard_id, etc.)
        if isinstance(v, dict):
            if k in ('id', 'value', 'count') or k.endswith('_id'):
                v.pop('description', None)
                v.pop('format', None)
                if v.get('type') in ('string', 'integer', 'number'):
                    v['type'] = ['null', 'string']
        # Allow NULL for all field types
        if k == 'type' and v in ('string', 'integer', 'boolean', 'number', 'object', 'array'):
            this_dict.pop('description', None)
            if v == 'object':
                this_dict['additionalProperties'] = False
                this_dict['type'] = ['null', 'object']
            arr = ['null']
            arr.append(v)
            this_dict[k] = arr
        # Remove extra format nodes
        if k == 'format' and v in ('uri', 'int64', 'double'):
            this_dict.pop(k, None)
        # Add additionalProperties = False to object nodes and remove Looker-specific nodes
        if k == 'properties':
            this_dict['additionalProperties'] = False
            if this_dict.get('type') == 'object' or this_dict.get('type') == ['null', 'object']:
                this_dict['type'] = ['null', 'object']
            this_dict.pop('x-looker-status', None)
            this_dict.pop('required', None)
        # Fix schema definition for color_collections color offset
        if k == 'color':
            this_offset = this_dict.get('offset')
            if this_offset:
                this_dict['offset'] = {"type": ["null", "number"], "multipleOf": 1e-16}
        # Remove Looker-specific nodes and loop thru dictionary keys
        if isinstance(v, dict):
            v.pop('readOnly', None)
            v.pop('can', None)
            v.pop('x-looker-nullable', None)
            v.pop('x-looker-values', None)
            v.pop('x-looker-status', None)
            v.pop('x-looker-write-only', None)
            tranform_looker_schemas(v)
        # Loop thru array lists
        elif isinstance(v, list):
            for i in list(v):
                if isinstance(i, dict):
                    tranform_looker_schemas(i)
    return this_dict


# Create a Singer JSON Schema from Looker Swagger endpoint
def get_transform_schema(client, stream_swagger_object, stream_name):
    LOGGER.info('Starting transform: %s', stream_name)
    endpoint = 'swagger.json'
    swagger = client.request(method='GET', path=endpoint, endpoint=endpoint)
    schema = swagger.get('definitions', {}).get(stream_swagger_object, {})
    new_schema = tranform_looker_schemas(replace_refs(schema, swagger))

    # Fix issue with ui_cofig and field for DashboardFilter
    if stream_name == 'dashboard_filters':
        LOGGER.info('Transforming JSON schema: %s', stream_name)
        new_schema['properties']['field'] = {"type": ["null", "object"], \
            'additionalProperties': True}
        new_schema['properties']['ui_config'] = {"type": ["null", "object"], \
            'additionalProperties': True}
        new_schema['properties']['ui_config'] = {"type": ["null", "object"], \
            'additionalProperties': True}

    # Fix issue with ui_cofig and field for DashboardFilter
    elif stream_name == 'dashboard_elements':
        LOGGER.info('Transforming JSON schema: %s', stream_name)
        new_schema['properties']['look']['properties']['query']['properties']['filter_config'] = \
            {"type": ["null", "object"], 'additionalProperties': True}
        new_schema['properties']['look']['properties']['query']['properties']['filters'] = \
            {"type": ["null", "object"], 'additionalProperties': True}
        new_schema['properties']['look']['properties']['query']['properties']['vis_config'] = \
            {"type": ["null", "object"], 'additionalProperties': True}
        new_schema['properties']['look']['properties']['query']['properties']['sorts'] = \
            {"type": ["null", "array"], "items": {}}
        new_schema['properties']['query']['properties']['filter_config'] = \
            {"type": ["null", "object"], 'additionalProperties': True}
        new_schema['properties']['query']['properties']['filters'] = \
            {"type": ["null", "object"], 'additionalProperties': True}
        new_schema['properties']['query']['properties']['vis_config'] = \
            {"type": ["null", "object"], 'additionalProperties': True}
        new_schema['properties']['query']['properties']['sorts'] = \
            {"type": ["null", "array"], "items": {}}
        new_schema['properties']['result_maker']['properties']['query']['properties']['filter_config'] = \
            {"type": ["null", "object"], 'additionalProperties': True}
        new_schema['properties']['result_maker']['properties']['query']['properties']['filters'] = \
            {"type": ["null", "object"], 'additionalProperties': True}
        new_schema['properties']['result_maker']['properties']['query']['properties']['vis_config'] = \
            {"type": ["null", "object"], 'additionalProperties': True}
        new_schema['properties']['result_maker']['properties']['query']['properties']['sorts'] = \
            {"type": ["null", "array"], "items": {}}
        new_schema['properties']['result_maker']['properties']['vis_config'] = \
            {"type": ["null", "object"], 'additionalProperties': True}
        new_schema['properties']['result_maker']['properties']['sorts'] = \
            {"type": ["null", "array"], "items": {}}

    # Fix issues with datatypes in DBConnection schema
    elif stream_name == 'connections':
        LOGGER.info('Transforming JSON schema: %s', stream_name)
        new_schema['properties']['last_regen_at'] = {"type": ["null", "integer"]}
        new_schema['properties']['last_reap_at'] = {"type": ["null", "integer"]}
        new_schema['properties']['max_billing_gigabytes'] = \
            {"type": ["null", "number"], "multipleOf": 1e-8}

    # Add parent_id node to Group
    elif stream_name == 'groups_in_group':
        LOGGER.info('Transforming JSON schema: %s', stream_name)
        new_schema['properties']['parent_group_id'] = {"type": ["null", "string"]}

    # Fix issue for Explore field enumerations value (string OR number)
    elif stream_name == 'explores':
        LOGGER.info('Transforming JSON schema: %s', stream_name)
        new_schema['properties']['fields']['properties']['dimensions']['items']['properties']['enumerations']['items']['properties']['value'] = \
            {"type": ["null", "string"]}
        new_schema['properties']['fields']['properties']['dimensions']['items']['properties']['time_interval']['properties']['count'] = \
            {"type": ["null", "string"]}

    # Add role_id node to Role Groups
    elif stream_name == 'role_groups':
        LOGGER.info('Transforming JSON schema: %s', stream_name)
        new_schema['properties']['role_id'] = {"type": ["null", "string"]}

    # Fix issue with ui_state for User
    elif stream_name == 'users':
        LOGGER.info('Transforming JSON schema: %s', stream_name)
        new_schema['properties']['ui_state'] = {"type": ["null", "object"], \
            'additionalProperties': True}
        new_schema['properties']['home_folder_id'] = {"type": ["null", "string"], \
            'additionalProperties': True}
        new_schema['properties']['personal_folder_id'] = {"type": ["null", "string"], \
            'additionalProperties': True}

    # Fix issue for UserAttribute value (string OR number)
    elif stream_name in ('user_attribute_group_values', 'user_attribute_values'):
        LOGGER.info('Transforming JSON schema: %s', stream_name)
        new_schema['properties']['value'] = {"type": ["null", "string"]}

    # Add parent_id nodes to GitBranch and ProjectFile
    elif stream_name in ('project_files', 'git_branches'):
        LOGGER.info('Transforming JSON schema: %s', stream_name)
        new_schema['properties']['project_id'] = {"type": ["null", "string"]}

    # Fix issues with Query filters, sorts, and cofigs
    elif stream_name == 'queries':
        LOGGER.info('Transforming JSON schema: %s', stream_name)
        new_schema['properties']['filter_config'] = {"type": ["null", "object"], \
            'additionalProperties': True}
        new_schema['properties']['filters'] = {"type": ["null", "object"], \
            'additionalProperties': True}
        new_schema['properties']['vis_config'] = {"type": ["null", "object"], \
            'additionalProperties': True}
        new_schema['properties']['sorts'] = {"type": ["null", "array"], "items": {}}
 
    # Fix issues with MergeQuery sorts and config
    elif stream_name == 'merge_queries':
        LOGGER.info('Transforming JSON schema: %s', stream_name)
        new_schema['properties']['vis_config'] = {"type": ["null", "object"], \
            'additionalProperties': True}
        new_schema['properties']['sorts'] = {"type": ["null", "array"], "items": {}}

    return new_schema


# DATA Transforms
def remove_can_nodes(this_json):
    new_json = this_json
    new_json.pop('can', None)
    for key, val in list(new_json.items()):
        if isinstance(val, dict):
            val.pop('can', None)
            remove_can_nodes(val)
        elif isinstance(val, list):
            for i in list(val):
                if isinstance(i, dict):
                    remove_can_nodes(i)
    return new_json


# Create MD5 hash key for data element
def hash_data(data):
    # Prepare the project id hash
    hashId = hashlib.md5()
    hashId.update(repr(data).encode('utf-8'))
    return hashId.hexdigest()


# query_history: Replace decimals with underscores in key
def transform_query_history(this_json):
    new_json = this_json
    dim_vals = []
    for key, val in list(new_json.items()):
        new_key = key.replace('.', '_')
        new_json[new_key] = val
        new_json.pop(key, None)
        if new_key not in ('query_id', 'history_created_date', 'history_query_run_count', 'history_total_runtime'):
            if not val:
                new_val = key
            else:
                new_val = '{}'.format(val)
            dim_vals.append(new_val)
        dims_hash_key = str(hash_data(sorted(dim_vals)))
        new_json['dims_hash_key'] = dims_hash_key
    return new_json


# Convert ALL ID fields to Strings; solves Looker Swagger schema inconsistency
# #   IDs that can be EITHER integer or string (space_id, dashboard_id, etc.)
def ids_to_string(this_dict):
    if this_dict:
        for key, val in list(this_dict.items()):
            # Convert value and count fields from number/string to string
            if key in ('value', 'count') and isinstance(val, numbers.Number):
                new_val = str('{}'.format(val))
                this_dict[key] = new_val
            if isinstance(val, int):
                if key == 'id' or key.endswith('_id'):
                    new_val = str('{}'.format(val))
                    this_dict[key] = new_val
            # Loop thru dictionary keys
            elif isinstance(val, dict):
                ids_to_string(val)
            # Loop thru array lists
            elif isinstance(val, list):
                for i in list(val):
                    if isinstance(i, dict):
                        ids_to_string(i)
            else:
                if val is None:
                    this_dict.pop(key, None)
    return this_dict


# Run other transforms, as needed: denest_list_nodes, transform_conversation_parts
def transform_json(this_json, stream_name):
    uncanny_json = remove_can_nodes(this_json)
    adjusted_json = None
    if stream_name == 'dashboards':
        # Remove LookML Dashboards
        if isinstance(uncanny_json.get('id'), str):
            adjusted_json = None
        else:
            adjusted_json = uncanny_json
    elif stream_name == 'lookml_dashboards':
        # Remove User Defined Dashboards
        if isinstance(uncanny_json.get('id'), int):
            adjusted_json = None
        else:
            adjusted_json = uncanny_json
    elif stream_name in ('user_attribute_group_values', 'user_attribute_values'):
        this_value = str('{}'.format(uncanny_json.get('value')))
        uncanny_json['value'] = this_value
        adjusted_json = uncanny_json
    elif stream_name == 'query_history':
        adjusted_json = transform_query_history(uncanny_json)
    else:
        adjusted_json = uncanny_json
    transformed_json = ids_to_string(adjusted_json)

    return transformed_json
