import json
import singer
from singer import metrics, metadata, utils, Transformer

from tap_looker.client import Server5xxError
from tap_looker.transform import transform_json
from tap_looker.streams import STREAMS

LOGGER = singer.get_logger()

def write_schema(catalog, stream_name):
    stream = catalog.get_stream(stream_name)
    schema = stream.schema.to_dict()
    try:
        singer.write_schema(stream_name, schema, stream.key_properties)
    except OSError as err:
        LOGGER.info('OS Error writing schema for: %s', stream_name)
        raise err


def write_record(catalog, stream_name, url, record, time_extracted):
    try:
        singer.messages.write_record(stream_name, record, time_extracted=time_extracted)
    except OSError as err:
        stream = catalog.get_stream(stream_name)
        schema = stream.schema.to_dict()
        LOGGER.info('\n\n%s URL: %s\n\n', stream_name, url)
        LOGGER.info('%s schema:', stream_name)
        LOGGER.info(json.dumps(schema, indent=2, sort_keys=True))
        LOGGER.info('\n\nOS Error writing record for: %s, record:', stream_name)
        LOGGER.info(json.dumps(record, indent=2, sort_keys=True))
        raise err


def get_bookmark(state, stream, default):
    if (state is None) or ('bookmarks' not in state):
        return default
    return (state .get('bookmarks', {}) .get(stream, default))


def write_bookmark(state, stream, value):
    if 'bookmarks' not in state:
        state['bookmarks'] = {}
    state['bookmarks'][stream] = value
    LOGGER.info('Write state for stream: %s, value: %s', stream, value)
    singer.write_state(state)


def transform_datetime(this_dttm):
    with Transformer() as transformer:
        new_dttm = transformer._transform_datetime(this_dttm)
    return new_dttm


def process_records(catalog, #pylint: disable=too-many-branches
                    stream_name,
                    records,
                    time_extracted,
                    bookmark_field=None,
                    max_bookmark_value=None,
                    last_datetime=None,
                    parent=None,
                    parent_id=None,
                    url=None):
    stream = catalog.get_stream(stream_name)
    schema = stream.schema.to_dict()
    stream_metadata = metadata.to_map(stream.metadata)

    with metrics.record_counter(stream_name) as counter:
        for record in records:
            # If child object, add parent_id to record
            if parent_id and parent:
                LOGGER.info('%s_id = %s', parent, parent_id)
                record['{}_id'.format(parent)] = parent_id

            # Transform record for Singer.io
            with Transformer() as transformer:
                transformed_record = transformer.transform(
                    record,
                    schema,
                    stream_metadata)

                # Reset max_bookmark_value to new value if higher
                if transformed_record.get(bookmark_field):
                    if max_bookmark_value is None or \
                        transformed_record[bookmark_field] > transform_datetime(max_bookmark_value):
                        max_bookmark_value = transformed_record[bookmark_field]

                if bookmark_field and (bookmark_field in transformed_record):
                    last_dttm = transform_datetime(last_datetime)
                    bookmark_dttm = transform_datetime(transformed_record[bookmark_field])
                    # Keep only records whose bookmark is after the last_datetime
                    if bookmark_dttm >= last_dttm:
                        write_record(catalog, stream_name, url, transformed_record, \
                            time_extracted=time_extracted)
                        counter.increment()
                else:
                    write_record(catalog, stream_name, url, transformed_record, \
                        time_extracted=time_extracted)
                    counter.increment()

        return max_bookmark_value, counter.value


# Sync a specific parent or child endpoint.
def sync_endpoint(client, #pylint: disable=too-many-branches
                  catalog,
                  state,
                  start_date,
                  stream_name,
                  path,
                  method,
                  endpoint_config,
                  bookmark_field=None,
                  id_fields=None,
                  selected_streams=None,
                  parent=None,
                  parent_id=None):

    LOGGER.info('STARTING Stream: %s', stream_name)
    # Get the latest bookmark for the stream and set the last_datetime
    last_datetime = get_bookmark(state, stream_name, start_date)
    max_bookmark_value = last_datetime

    # pagination: there is no pagination for Looker API
    url = '{}/{}'.format(client.base_url, path)
    LOGGER.info('URL for %s: %s', stream_name, url)

    # Get data, API request
    body = endpoint_config.get('body')
    data = []
    try:
        data = client.request(
            method=method,
            path=path,
            endpoint=stream_name,
            json=body)
    except Server5xxError as err:
        LOGGER.warning('Server 5xx Error: %s', err)
        LOGGER.warning('Error URL: %s', url)
        return 0

    # time_extracted: datetime when the data was extracted from the API
    time_extracted = utils.now()

    # LOGGER.info('{}, data = {}'.format(stream_name, data)) # TESTING, comment out
    data_set = [] # initialize the data_set record list

    # If data is a single-record dict (like shop endpoint), add it to a list
    if isinstance(data, dict):
        data_set.append(data)
    elif isinstance(data, list):
        data_set = data
    else:
        return 0

    # Transform data_set records to transformed_data
    transformed_data = []
    records_queried = 0
    for record in data_set:
        transformed_record = transform_json(record, stream_name)
        if transformed_record:
            transformed_data.append(transformed_record)
            records_queried = records_queried + 1

    if stream_name == 'models':
        child_list = []
        for record in transformed_data:
            if 'explores' in record:
                for explore in record['explores']:
                    explore_name = explore.get('name')
                    if explore_name:
                        child_list.append(explore_name)
        LOGGER.info('child_list: %s', child_list)
    else:
        child_list = ['self']

    # Process records and get the max_bookmark_value and record_count for the set of records
    max_bookmark_value, records_processed = process_records(
        catalog=catalog,
        stream_name=stream_name,
        records=transformed_data,
        time_extracted=time_extracted,
        bookmark_field=bookmark_field,
        max_bookmark_value=max_bookmark_value,
        last_datetime=last_datetime,
        parent=parent,
        parent_id=parent_id,
        url=url)

    # Loop thru parent batch records for each children objects (if should stream)
    children = endpoint_config.get('children')
    if children:
        for child_stream_name, child_endpoint_config in children.items():
            if child_stream_name in selected_streams:
                write_schema(catalog, child_stream_name)
                # For each parent record
                for record in transformed_data:
                    i = 0
                    if stream_name == 'users' and child_stream_name in (
                        'user_sessions', 'content_favorites', 'content_views'):
                        # Skip disabled users which result in 500 errors
                        is_disabled = record.get('is_disabled', False)
                        if is_disabled:
                            continue
                    # Set parent_id
                    parent_id_field = None
                    for id_field in id_fields:
                        if i == 0:
                            parent_id_field = id_field
                        if id_field == 'id':
                            parent_id_field = id_field
                        i = i + 1
                    do_pass = True
                    if parent_id_field:
                        parent_id = record.get(parent_id_field)
                    child_path = None
                    if parent_id:
                        child_path = child_endpoint_config.get('path').format(str(parent_id))
                    else:
                        do_pass = False

                    content_metadata_id = record.get('content_metadata_id')
                    if content_metadata_id:
                        child_path = child_path.replace('[content_metadata_id]', \
                            str(content_metadata_id))
                    elif child_stream_name in ['content_metadata', 'content_metadata_access']:
                        do_pass = False

                    query_id = record.get('query_id')
                    if query_id:
                        child_path = child_path.replace('[query_id]', str(query_id))
                    elif child_stream_name == 'queries':
                        do_pass = False

                    merge_result_id = record.get('merge_result_id')
                    if merge_result_id:
                        child_path = child_path.replace('[merge_result_id]', str(merge_result_id))
                    elif child_stream_name == 'merge_queries':
                        do_pass = False

                    if not do_pass:
                        LOGGER.info('%s, PATH does not pass: %s', child_stream_name, \
                            child_path)
                    else:
                        for child in child_list:
                            if child != 'self':
                                child_path = child_path.replace('[child_id]', str(child))
                            LOGGER.info('Syncing: %s, %s, parent_stream: %s, parent_id: %s',
                                        child_stream_name,
                                        child,
                                        stream_name,
                                        parent_id)

                            LOGGER.info('%s, child_path: %s', child_stream_name, child_path)
                            child_total_records = sync_endpoint(
                                client=client,
                                catalog=catalog,
                                state=state,
                                start_date=start_date,
                                stream_name=child_stream_name,
                                path=child_path,
                                endpoint_config=child_endpoint_config,
                                bookmark_field=child_endpoint_config.get('bookmark_field'),
                                method=child_endpoint_config.get('method', 'GET'),
                                id_fields=child_endpoint_config.get('key_properties'),
                                selected_streams=selected_streams,
                                parent=child_endpoint_config.get('parent'),
                                parent_id=parent_id)
                            LOGGER.info('Synced: %s, parent_id: %s, records_processed: %s',
                                        child_stream_name,
                                        parent_id,
                                        child_total_records)

    LOGGER.info('%s: records_queried = %s, records_processed = %s',
                stream_name, records_queried, records_processed)
    # Return the list of ids to the stream, in case this is a parent stream with children.
    LOGGER.info('FINISHING Stream: %s', stream_name)
    return records_processed


# Currently syncing sets the stream currently being delivered in the state.
# If the integration is interrupted, this state property is used to identify
#  the starting point to continue from.
# Reference: https://github.com/singer-io/singer-python/blob/master/singer/bookmarks.py#L41-L46
def update_currently_syncing(state, stream_name):
    if (stream_name is None) and ('currently_syncing' in state):
        del state['currently_syncing']
    else:
        singer.set_currently_syncing(state, stream_name)
    singer.write_state(state)


# List selected fields from stream catalog
def get_selected_fields(catalog, stream_name):
    stream = catalog.get_stream(stream_name)
    mdata = metadata.to_map(stream.metadata)
    mdata_list = singer.metadata.to_list(mdata)
    selected_fields = []
    for entry in mdata_list:
        field = None
        try:
            field = entry['breadcrumb'][1]
            if entry.get('metadata', {}).get('selected', False):
                selected_fields.append(field)
        except IndexError:
            pass
    return selected_fields

def sync(client, config, catalog, state):
    start_date = config.get('start_date')

    # Get selected_streams from catalog, based on state last_stream
    #   last_stream = Previous currently synced stream, if the load was interrupted
    last_stream = singer.get_currently_syncing(state)
    LOGGER.info('last/currently syncing stream: %s', last_stream)
    selected_streams = []
    for stream in catalog.get_selected_streams(state):
        selected_streams.append(stream.stream)
    LOGGER.info('selected_streams: %s', selected_streams)

    if not selected_streams:
        return

    # Loop through selected_streams
    for stream_name, endpoint_config in STREAMS.items():
        if stream_name in selected_streams:
            LOGGER.info('START Syncing: %s', stream_name)
            selected_fields = get_selected_fields(catalog, stream_name)
            LOGGER.info('Stream: %s, selected_fields: %s', stream_name, selected_fields)
            update_currently_syncing(state, stream_name)
            path = endpoint_config.get('path', stream_name)
            bookmark_field = next(iter(endpoint_config.get('replication_keys', [])), None)
            write_schema(catalog, stream_name)
            total_records = sync_endpoint(
                client=client,
                catalog=catalog,
                state=state,
                start_date=start_date,
                stream_name=stream_name,
                path=path,
                endpoint_config=endpoint_config,
                method=endpoint_config.get('method', 'GET'),
                bookmark_field=bookmark_field,
                id_fields=endpoint_config.get('key_properties'),
                selected_streams=selected_streams)

            update_currently_syncing(state, None)
            LOGGER.info('FINISHED Syncing: %s, total_records: %s',
                        stream_name,
                        total_records)
