import os
import json
import singer
from singer import metadata
from tap_looker.streams import flatten_streams
from tap_looker.transform import get_transform_schema

LOGGER = singer.get_logger()

# Reference:
# https://github.com/singer-io/getting-started/blob/master/docs/DISCOVERY_MODE.md#Metadata

def get_abs_path(path):
    return os.path.join(os.path.dirname(os.path.realpath(__file__)), path)


# DEVELOPMENT ONLY. Run from generate_schemas.py to create initial drafts of JSON Schems
#   from the Looker API Swagger Definitions file.
def generate_schemas(client):
    flat_streams = flatten_streams()
    cwd = os.getcwd()
    flat_streams_list = []
    for stream_name, stream_metadata in flat_streams.items():
        # Skip any non-Swagger object (e.g. query_history)
        if not(stream_name == 'query_history'):
            if stream_name not in flat_streams_list:
                flat_streams_list.append(stream_name)
            swagger_object = stream_metadata.get('swagger_object')
            schema = get_transform_schema(client, swagger_object, stream_name)
            schema_path = get_abs_path('{}/tap_looker/schemas/{}.json'.format(cwd, stream_name))
            with open(schema_path, 'w', encoding='utf-8') as file:
                json.dump(schema, file, ensure_ascii=False, indent=2, sort_keys=True)
    LOGGER.info('Generated schemas for: %s', sorted(flat_streams_list))


def get_schemas():
    schemas = {}
    field_metadata = {}

    flat_streams = flatten_streams()
    for stream_name, stream_metadata in flat_streams.items():
        schema_path = get_abs_path('schemas/{}.json'.format(stream_name))
        with open(schema_path) as file:
            schema = json.load(file)
        schemas[stream_name] = schema
        mdata = metadata.new()

        # Documentation:
        # https://github.com/singer-io/getting-started/blob/master/docs/DISCOVERY_MODE.md#singer-python-helper-functions
        # Reference:
        # https://github.com/singer-io/singer-python/blob/master/singer/metadata.py#L25-L44
        mdata = metadata.get_standard_metadata(
            schema=schema,
            key_properties=stream_metadata.get('key_properties', None),
            valid_replication_keys=stream_metadata.get('replication_keys', None),
            replication_method=stream_metadata.get('replication_method', None)
        )
        field_metadata[stream_name] = mdata

    return schemas, field_metadata
