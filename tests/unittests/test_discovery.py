import unittest
from unittest.mock import MagicMock, patch

from tap_looker.client import LookerForbiddenError
from tap_looker.discover import (
    PARENT_STREAM_PATHS,
    _apply_access_checks,
    _prune_inaccessible_children,
    discover,
)
from tap_looker.streams import STREAMS, build_child_parent_map


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_schemas():
    """Return a minimal schemas/field_metadata pair covering all flat streams."""
    from tap_looker.streams import flatten_streams
    flat = flatten_streams()
    schemas = {name: {'properties': {}} for name in flat}
    field_metadata = {name: [] for name in flat}
    return schemas, field_metadata


def _make_client(forbidden_streams=None):
    """
    Return a mock LookerClient.
    Streams whose name matches an entry in forbidden_streams raise LookerForbiddenError.
    """
    forbidden_streams = set(forbidden_streams or [])
    client = MagicMock()

    def _request(method, path=None, url=None, endpoint=None, **kwargs):
        if endpoint in forbidden_streams:
            raise LookerForbiddenError(
                f'HTTP-error-code: 403, Error: Forbidden ({endpoint})'
            )
        return {}

    client.request.side_effect = _request
    return client


# ---------------------------------------------------------------------------
# Tests for build_child_parent_map
# ---------------------------------------------------------------------------

class TestBuildChildParentMap(unittest.TestCase):
    def setUp(self):
        self.child_map = build_child_parent_map()

    def test_direct_children_mapped_to_parent(self):
        """Direct children of dashboards are mapped to 'dashboards'."""
        self.assertIn('dashboards', self.child_map.get('dashboard_elements', set()))
        self.assertIn('dashboards', self.child_map.get('dashboard_filters', set()))

    def test_grandchildren_mapped_to_child_parent(self):
        """explores is a grandchild of lookml_models via models."""
        self.assertIn('models', self.child_map.get('explores', set()))

    def test_deep_nesting_three_levels(self):
        """queries is mapped to merge_queries (3rd level: dashboards->dashboard_elements->merge_queries->queries)."""
        self.assertIn('merge_queries', self.child_map.get('queries', set()))

    def test_parent_streams_not_in_map(self):
        """Streams that are never listed as a child anywhere in STREAMS must not appear in child_map."""
        def _all_child_names(streams_dict):
            found = set()
            for config in streams_dict.values():
                children = config.get('children', {})
                if children:
                    found.update(children.keys())
                    found.update(_all_child_names(children))
            return found

        never_a_child = set(STREAMS.keys()) - _all_child_names(STREAMS)
        for name in never_a_child:
            self.assertNotIn(
                name, self.child_map,
                f"'{name}' is never a child stream but appears in the child-parent map",
            )

    def test_users_children_mapped(self):
        for child in ('user_attribute_values', 'user_sessions',
                      'content_favorites', 'content_views'):
            self.assertIn('users', self.child_map.get(child, set()))


# ---------------------------------------------------------------------------
# Tests for _prune_inaccessible_children
# ---------------------------------------------------------------------------

class TestPruneInaccessibleChildren(unittest.TestCase):
    def test_child_removed_when_sole_parent_absent(self):
        """groups_in_group is removed when groups (its only parent) is absent."""
        schemas = {'groups_in_group': {}}
        field_metadata = {'groups_in_group': []}

        _prune_inaccessible_children(schemas, field_metadata)

        self.assertNotIn('groups_in_group', schemas)
        self.assertNotIn('groups_in_group', field_metadata)

    def test_child_kept_when_parent_present(self):
        """groups_in_group is kept when groups is still in schemas."""
        schemas = {'groups': {}, 'groups_in_group': {}}
        field_metadata = {'groups': [], 'groups_in_group': []}

        _prune_inaccessible_children(schemas, field_metadata)

        self.assertIn('groups_in_group', schemas)

    def test_grandchild_cascades_after_parent_removed(self):
        """explores is removed when models is removed (which was child of lookml_models)."""
        # Remove lookml_models, keep models listed but then models will be removed
        # because its parent (lookml_models) is gone. explores should follow.
        schemas = {'models': {}, 'explores': {}}
        field_metadata = {'models': [], 'explores': []}

        _prune_inaccessible_children(schemas, field_metadata)

        self.assertNotIn('models', schemas)
        self.assertNotIn('explores', schemas)

    def test_child_with_multiple_parents_kept_if_one_parent_present(self):
        """queries is kept when 'looks' (a top-level parent) is still accessible."""
        # queries has parents: dashboard_elements, merge_queries, looks.
        # 'looks' is a top-level stream and has no parent itself, so it won't be
        # cascaded-away. Include it alongside queries to verify retention.
        schemas = {'queries': {}, 'looks': {}}
        field_metadata = {'queries': [], 'looks': []}

        _prune_inaccessible_children(schemas, field_metadata)

        self.assertIn('queries', schemas)

    def test_child_removed_when_all_parents_absent(self):
        """queries is removed only when ALL its parent streams are absent."""
        schemas = {'queries': {}}
        field_metadata = {'queries': []}

        _prune_inaccessible_children(schemas, field_metadata)

        self.assertNotIn('queries', schemas)

    def test_unrelated_stream_untouched(self):
        schemas = {'color_collections': {}, 'versions': {}}
        field_metadata = {'color_collections': [], 'versions': []}

        _prune_inaccessible_children(schemas, field_metadata)

        self.assertIn('color_collections', schemas)
        self.assertIn('versions', schemas)


# ---------------------------------------------------------------------------
# Tests for _apply_access_checks
# ---------------------------------------------------------------------------

class TestApplyAccessChecks(unittest.TestCase):
    def test_all_accessible_no_removals(self):
        """No streams removed when all parent probes return 200."""
        client = _make_client()
        schemas, field_metadata = _make_schemas()
        original_count = len(schemas)

        _apply_access_checks(client, schemas, field_metadata)

        self.assertEqual(len(schemas), original_count)

    def test_forbidden_parent_removed(self):
        client = _make_client(forbidden_streams=['dashboards'])
        schemas, field_metadata = _make_schemas()

        _apply_access_checks(client, schemas, field_metadata)

        self.assertNotIn('dashboards', schemas)
        self.assertNotIn('dashboards', field_metadata)

    def test_forbidden_parent_children_removed(self):
        """dashboard_elements and its siblings are removed when dashboards is forbidden.

        Note: 'scheduled_plans' is also a top-level parent stream in STREAMS and has
        other parents (lookml_dashboards, looks), so it is NOT removed when only
        dashboards is forbidden.
        """
        client = _make_client(forbidden_streams=['dashboards'])
        schemas, field_metadata = _make_schemas()

        _apply_access_checks(client, schemas, field_metadata)

        # Pure children of dashboards only — scheduled_plans has additional parents
        for child in ('dashboard_elements', 'dashboard_filters', 'dashboard_layouts'):
            self.assertNotIn(child, schemas)
        # scheduled_plans survives because lookml_dashboards / looks are still accessible
        self.assertIn('scheduled_plans', schemas)

    def test_all_parents_forbidden_raises(self):
        """LookerForbiddenError raised when every parent stream is forbidden."""
        client = _make_client(forbidden_streams=list(PARENT_STREAM_PATHS.keys()))
        schemas, field_metadata = _make_schemas()

        with self.assertRaises(LookerForbiddenError):
            _apply_access_checks(client, schemas, field_metadata)

    def test_partial_access_does_not_raise(self):
        """No exception when at least one parent is accessible."""
        all_but_one = list(PARENT_STREAM_PATHS.keys())[:-1]
        client = _make_client(forbidden_streams=all_but_one)
        schemas, field_metadata = _make_schemas()

        try:
            _apply_access_checks(client, schemas, field_metadata)
        except LookerForbiddenError:
            self.fail('LookerForbiddenError raised unexpectedly')

    def test_probe_calls_correct_paths(self):
        """client.request is invoked with the correct path and endpoint for each parent stream."""
        client = _make_client()
        schemas, field_metadata = _make_schemas()

        _apply_access_checks(client, schemas, field_metadata)

        # Build a map of endpoint -> path from the actual calls
        called = {}
        for c in client.request.call_args_list:
            endpoint = c.kwargs.get('endpoint')
            path = c.kwargs.get('path')
            if endpoint is not None:
                called[endpoint] = path

        for stream_name, expected_path in PARENT_STREAM_PATHS.items():
            self.assertIn(stream_name, called,
                          f"Stream '{stream_name}' was never probed")
            self.assertEqual(called[stream_name], expected_path,
                             f"Stream '{stream_name}' probed with wrong path: "
                             f"got '{called[stream_name]}', expected '{expected_path}'")

    def test_field_metadata_pruned_alongside_schema(self):
        client = _make_client(forbidden_streams=['users'])
        schemas, field_metadata = _make_schemas()

        _apply_access_checks(client, schemas, field_metadata)

        self.assertNotIn('users', field_metadata)
        self.assertNotIn('user_sessions', field_metadata)


# ---------------------------------------------------------------------------
# Tests for discover()
# ---------------------------------------------------------------------------

class TestDiscover(unittest.TestCase):
    @patch('tap_looker.discover.get_schemas')
    def test_discover_returns_all_streams_when_accessible(self, mock_get_schemas):
        from tap_looker.streams import flatten_streams
        flat = flatten_streams()
        mock_schemas = {name: {'properties': {}} for name in flat}
        mock_metadata = {name: [] for name in flat}
        mock_get_schemas.return_value = (mock_schemas, mock_metadata)

        client = _make_client()
        catalog = discover(client)

        stream_ids = {s.tap_stream_id for s in catalog.streams}
        self.assertEqual(stream_ids, set(flat.keys()))

    @patch('tap_looker.discover.get_schemas')
    def test_discover_excludes_forbidden_stream_and_children(self, mock_get_schemas):
        from tap_looker.streams import flatten_streams
        flat = flatten_streams()
        mock_schemas = {name: {'properties': {}} for name in flat}
        mock_metadata = {name: [] for name in flat}
        mock_get_schemas.return_value = (mock_schemas, mock_metadata)

        client = _make_client(forbidden_streams=['users'])
        catalog = discover(client)

        stream_ids = {s.tap_stream_id for s in catalog.streams}
        self.assertNotIn('users', stream_ids)
        for child in ('user_attribute_values', 'user_sessions',
                      'content_favorites', 'content_views'):
            self.assertNotIn(child, stream_ids)

    @patch('tap_looker.discover.get_schemas')
    def test_discover_raises_when_all_parents_forbidden(self, mock_get_schemas):
        from tap_looker.streams import flatten_streams
        flat = flatten_streams()
        mock_schemas = {name: {'properties': {}} for name in flat}
        mock_metadata = {name: [] for name in flat}
        mock_get_schemas.return_value = (mock_schemas, mock_metadata)

        client = _make_client(forbidden_streams=list(PARENT_STREAM_PATHS.keys()))
        with self.assertRaises(LookerForbiddenError):
            discover(client)

    @patch('tap_looker.discover.get_schemas')
    def test_discover_does_not_mutate_schema_cache(self, mock_get_schemas):
        """The dict returned by get_schemas must not be modified by access checks."""
        from tap_looker.streams import flatten_streams
        flat = flatten_streams()
        mock_schemas = {name: {'properties': {}} for name in flat}
        mock_metadata = {name: [] for name in flat}
        mock_get_schemas.return_value = (mock_schemas, mock_metadata)

        client = _make_client(forbidden_streams=['roles'])
        discover(client)

        # The original dicts passed back from get_schemas must still contain 'roles'
        self.assertIn('roles', mock_schemas)


if __name__ == '__main__':
    unittest.main()
