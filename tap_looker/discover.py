import singer
from singer.catalog import Catalog, CatalogEntry, Schema
from tap_looker.client import LookerForbiddenError
from tap_looker.schema import get_schemas
from tap_looker.streams import STREAMS, flatten_streams, build_child_parent_map

LOGGER = singer.get_logger()

def _get_parent_stream_paths():
    """Return {stream_name: probe_path} for all non-POST parent streams.
    """
    paths = {}
    for name, config in STREAMS.items():
        if config.get('method') != 'POST':
            paths[name] = config.get('path', name).split('?')[0]
    return paths


def _apply_access_checks(client, schemas: dict, field_metadata: dict) -> None:
    """
    Probe each parent stream for read access and remove inaccessible streams
    (and their descendants) from schemas and field_metadata in place.
    Raises LookerForbiddenError if no parent streams are accessible.
    """
    parent_paths = _get_parent_stream_paths()
    inaccessible_streams = []
    for stream_name, path in parent_paths.items():
        if stream_name not in schemas:
            continue
        try:
            client.request('GET', path=path, endpoint=stream_name)
        except LookerForbiddenError:
            LOGGER.warning(
                "Stream '%s' does not have read permission, excluding from catalog.",
                stream_name,
            )
            inaccessible_streams.append(stream_name)

    for stream_name in inaccessible_streams:
        schemas.pop(stream_name, None)
        field_metadata.pop(stream_name, None)

    _prune_inaccessible_children(schemas, field_metadata)

    if not schemas:
        raise LookerForbiddenError(
            "HTTP-error-code: 403, Error: The account credentials supplied do not have 'read' "
            "access to any of the streams supported by the tap. Data collection cannot be "
            "initiated due to lack of permissions."
        )

    if inaccessible_streams:
        LOGGER.warning(
            "The account credentials supplied do not have 'read' access to the following "
            "stream(s): %s. These streams have been excluded from the catalog.",
            ", ".join(inaccessible_streams),
        )


def _prune_inaccessible_children(schemas: dict, field_metadata: dict) -> None:
    """
    Remove child/grandchild streams whose parent stream was excluded from schemas.
    Runs iteratively until stable to handle multi-level cascading removal.
    Mutates schemas and field_metadata in place.
    """
    child_to_parents = build_child_parent_map()
    changed = True
    while changed:
        changed = False
        for child_name, parents in list(child_to_parents.items()):
            if child_name in schemas and all(p not in schemas for p in parents):
                LOGGER.warning(
                    "Stream '%s' excluded from catalog because all of its parent "
                    "stream(s) (%s) are not accessible.",
                    child_name,
                    ", ".join(sorted(parents)),
                )
                schemas.pop(child_name)
                field_metadata.pop(child_name, None)
                changed = True


def discover(client):
    schemas, field_metadata = get_schemas()
    # Copy to avoid mutating the module-level cache in schema.py
    schemas = dict(schemas)
    field_metadata = dict(field_metadata)

    _apply_access_checks(client, schemas, field_metadata)

    catalog = Catalog([])

    flat_streams = flatten_streams()
    for stream_name, schema_dict in schemas.items():
        schema = Schema.from_dict(schema_dict)
        mdata = field_metadata[stream_name]

        catalog.streams.append(CatalogEntry(
            stream=stream_name,
            tap_stream_id=stream_name,
            key_properties=flat_streams.get(stream_name, {}).get('key_properties', None),
            schema=schema,
            metadata=mdata
        ))

    return catalog
