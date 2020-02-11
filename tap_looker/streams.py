# streams: API URL endpoints to be called
# properties:
#   <root node>: Plural stream name for the endpoint
#   path: API endpoint relative path, when added to the base URL, creates the full path,
#       default = stream_name
#   key_properties: Primary key fields for identifying an endpoint record.
#   replication_method: INCREMENTAL or FULL_TABLE
#   replication_keys: bookmark_field(s), typically a date-time, used for filtering the results
#        and setting the state
#   params: Query, sort, and other endpoint specific parameters; default = {}
#   data_key: JSON element containing the results list for the endpoint; default = 'results'
#   bookmark_query_field: From date-time field used for filtering the query
#   swagger_object: Looker Swagger API object reference with definitions for JSON schemas

STREAMS = {
    'color_collections': {
        'key_properties': ['id'],
        'replication_method': 'FULL_TABLE',
        'swagger_object': 'ColorCollection'
    },
    'connections': {
        'key_properties': ['name'],
        'replication_method': 'FULL_TABLE',
        'swagger_object': 'DBConnection'
    },
    'dashboards': {
        'key_properties': ['id'],
        'replication_method': 'FULL_TABLE',
        'swagger_object': 'DashboardBase',
        'children': {
            'dashboard_elements': {
                'path': 'dashboards/{}/dashboard_elements',
                'key_properties': ['id'],
                'replication_method': 'FULL_TABLE',
                'swagger_object': 'DashboardElement',
                'children': {
                    'queries': {
                        'path': 'queries/[query_id]',
                        'key_properties': ['id'],
                        'replication_method': 'FULL_TABLE',
                        'swagger_object': 'Query'
                    },
                    'merge_queries': {
                        'path': 'merge_queries/[merge_result_id]',
                        'key_properties': ['id'],
                        'replication_method': 'FULL_TABLE',
                        'swagger_object': 'MergeQuery',
                        'children': {
                            'queries': {
                                'path': 'queries/[query_id]',
                                'key_properties': ['id'],
                                'replication_method': 'FULL_TABLE',
                                'swagger_object': 'Query'
                            }
                        }
                    }
                }
            },
            'dashboard_filters': {
                'path': 'dashboards/{}/dashboard_filters',
                'key_properties': ['id'],
                'replication_method': 'FULL_TABLE',
                'swagger_object': 'DashboardFilter'
            },
            'dashboard_layouts': {
                'path': 'dashboards/{}/dashboard_layouts',
                'key_properties': ['id'],
                'replication_method': 'FULL_TABLE',
                'swagger_object': 'DashboardLayout'
            },
            'content_metadata': {
                'path': 'content_metadata/[content_metadata_id]',
                'key_properties': ['id'],
                'replication_method': 'FULL_TABLE',
                'swagger_object': 'ContentMeta'
            },
            'scheduled_plans': {
                'path': 'scheduled_plans/dashboard/{}?all_users=true',
                'key_properties': ['id'],
                'replication_method': 'FULL_TABLE',
                'swagger_object': 'ScheduledPlan'
            }
        }
    },
    'datagroups': {
        'key_properties': ['id'],
        'replication_method': 'FULL_TABLE',
        'swagger_object': 'Datagroup'
    },
    'folders': {
        'key_properties': ['id'],
        'replication_method': 'FULL_TABLE',
        'swagger_object': 'Folder',
        'children': {
            'content_metadata': {
                'path': 'content_metadata?parent_id=[content_metadata_id]',
                'key_properties': ['id'],
                'replication_method': 'FULL_TABLE',
                'swagger_object': 'ContentMeta'
            },
            'content_metadata': {
                'path': 'content_metadata/[content_metadata_id]',
                'key_properties': ['id'],
                'replication_method': 'FULL_TABLE',
                'swagger_object': 'ContentMeta'
            },
            'content_metadata_access': {
                'path': 'content_metadata_access?content_metadata_id=[content_metadata_id]',
                'key_properties': ['id'],
                'replication_method': 'FULL_TABLE',
                'swagger_object': 'ContentMetaGroupUser'
            }
        }
    },
    'groups': {
        'key_properties': ['id'],
        'replication_method': 'FULL_TABLE',
        'swagger_object': 'Group',
        'children': {
            'groups_in_group': {
                'path': 'groups/{}/groups',
                'key_properties': ['id'],
                'replication_method': 'FULL_TABLE',
                'swagger_object': 'Group',
                'parent': 'parent_group'
            }
        }
    },
    'homepages': {
        'key_properties': ['id'],
        'replication_method': 'FULL_TABLE',
        'swagger_object': 'Homepage',
        'children': {
            'content_metadata': {
                'path': 'content_metadata/[content_metadata_id]',
                'key_properties': ['id'],
                'replication_method': 'FULL_TABLE',
                'swagger_object': 'ContentMeta'
            },
            'content_metadata_access': {
                'path': 'content_metadata_access?content_metadata_id=[content_metadata_id]',
                'key_properties': ['id'],
                'replication_method': 'FULL_TABLE',
                'swagger_object': 'ContentMetaGroupUser'
            }
        }
    },
    'integration_hubs': {
        'key_properties': ['id'],
        'replication_method': 'FULL_TABLE',
        'swagger_object': 'IntegrationHub'
    },
    'integrations': {
        'key_properties': ['id'],
        'replication_method': 'FULL_TABLE',
        'swagger_object': 'Integration'
    },
    'lookml_dashboards': {
        'path': 'dashboards',
        'key_properties': ['id'],
        'replication_method': 'FULL_TABLE',
        'swagger_object': 'DashboardBase',
        'children': {
            'scheduled_plans': {
                'path': 'scheduled_plans/lookml_dashboard/{}?all_users=true',
                'key_properties': ['id'],
                'replication_method': 'FULL_TABLE',
                'swagger_object': 'ScheduledPlan'
            }
        }
    },
    'lookml_models': {
        'key_properties': ['name', 'project_name'],
        'replication_method': 'FULL_TABLE',
        'swagger_object': 'LookmlModel',
        'children': {
            'models': {
                'path': 'lookml_models/{}',
                'key_properties': ['name', 'project_name'],
                'replication_method': 'FULL_TABLE',
                'swagger_object': 'LookmlModel',
                'children': {
                    'explores': {
                        'path': 'lookml_models/{}/explores/[child_id]',
                        'key_properties': ['id'],
                        'replication_method': 'FULL_TABLE',
                        'swagger_object': 'LookmlModelExplore'
                    }
                }
            }
        }
    },
    'looks': {
        'key_properties': ['id'],
        'replication_method': 'FULL_TABLE',
        'swagger_object': 'Look',
        'children': {
            'queries': {
                'path': 'queries/[query_id]',
                'key_properties': ['id'],
                'replication_method': 'FULL_TABLE',
                'swagger_object': 'Query'
            },
            'content_metadata': {
                'path': 'content_metadata/[content_metadata_id]',
                'key_properties': ['id'],
                'replication_method': 'FULL_TABLE',
                'swagger_object': 'ContentMeta'
            },
            'scheduled_plans': {
                'path': 'scheduled_plans/look/{}?all_users=true',
                'key_properties': ['id'],
                'replication_method': 'FULL_TABLE',
                'swagger_object': 'ScheduledPlan'
            }
        }
    },
    'model_sets': {
        'key_properties': ['id'],
        'replication_method': 'FULL_TABLE',
        'swagger_object': 'ModelSet'
    },
    'permission_sets': {
        'key_properties': ['id'],
        'replication_method': 'FULL_TABLE',
        'swagger_object': 'PermissionSet'
    },
    'permissions': {
        'key_properties': ['permission'],
        'replication_method': 'FULL_TABLE',
        'swagger_object': 'Permission'
    },
    'projects': {
        'key_properties': ['id'],
        'replication_method': 'FULL_TABLE',
        'swagger_object': 'Project',
        'children': {
            'project_files': {
                'path': 'projects/{}/files',
                'key_properties': ['id', 'project_id'],
                'replication_method': 'FULL_TABLE',
                'swagger_object': 'ProjectFile',
                'parent': 'project'
            },
            'git_branches': {
                'path': 'projects/{}/git_branches',
                'key_properties': ['name', 'project_id'],
                'replication_method': 'FULL_TABLE',
                'swagger_object': 'GitBranch',
                'parent': 'project'
            }
        }
    },
    'roles': {
        'key_properties': ['id'],
        'replication_method': 'FULL_TABLE',
        'swagger_object': 'Role',
        'children': {
            'role_groups': {
                'path': 'roles/{}/groups',
                'key_properties': ['id', 'role_id'],
                'replication_method': 'FULL_TABLE',
                'swagger_object': 'Group',
                'parent': 'role'
            }
        }
    },
    'scheduled_plans': {
        'path': 'scheduled_plans?all_users=true',
        'key_properties': ['id'],
        'replication_method': 'FULL_TABLE',
        'swagger_object': 'ScheduledPlan'
    },
    'spaces': {
        'key_properties': ['id'],
        'replication_method': 'FULL_TABLE',
        'swagger_object': 'Space',
        'children': {
            'content_metadata': {
                'path': 'content_metadata?parent_id=[content_metadata_id]',
                'key_properties': ['id'],
                'replication_method': 'FULL_TABLE',
                'swagger_object': 'ContentMeta'
            },
            'content_metadata': {
                'path': 'content_metadata/[content_metadata_id]',
                'key_properties': ['id'],
                'replication_method': 'FULL_TABLE',
                'swagger_object': 'ContentMeta'
            },
            'content_metadata_access': {
                'path': 'content_metadata_access?content_metadata_id=[content_metadata_id]',
                'key_properties': ['id'],
                'replication_method': 'FULL_TABLE',
                'swagger_object': 'ContentMetaGroupUser'
            }
        }
    },
    'themes': {
        'key_properties': ['id'],
        'replication_method': 'FULL_TABLE',
        'swagger_object': 'Theme'
    },
    'user_attributes': {
        'key_properties': ['id'],
        'replication_method': 'FULL_TABLE',
        'swagger_object': 'UserAttribute',
        'children': {
            'user_attribute_group_values': {
                'path': 'user_attributes/{}/group_values',
                'key_properties': ['id'],
                'replication_method': 'FULL_TABLE',
                'swagger_object': 'UserAttributeGroupValue'
            }
        }
    },
    'user_login_lockouts': {
        'key_properties': ['key'],
        'replication_method': 'FULL_TABLE',
        'swagger_object': 'UserLoginLockout'
    },
    'users': {
        'key_properties': ['id'],
        'replication_method': 'FULL_TABLE',
        'swagger_object': 'User',
        'children': {
            'user_attribute_values': {
                'path': 'users/{}/attribute_values?all_values=true&include_unset=true',
                'key_properties': ['user_id', 'user_attribute_id'],
                'replication_method': 'FULL_TABLE',
                'swagger_object': 'UserAttributeWithValue'
            },
            'user_sessions': {
                'path': 'users/{}/sessions',
                'key_properties': ['id'],
                'replication_method': 'FULL_TABLE',
                'swagger_object': 'Session'
            },
            'content_favorites': {
                'path': 'content_favorite/search?user_id={}',
                'key_properties': ['id'],
                'replication_method': 'FULL_TABLE',
                'swagger_object': 'ContentFavorite'
            },
            'content_views': {
                'path': 'content_view/search?user_id={}',
                'key_properties': ['id'],
                'replication_method': 'FULL_TABLE',
                'swagger_object': 'ContentView'
            }
        }
    },
    'versions': {
        'key_properties': ['looker_release_version'],
        'replication_method': 'FULL_TABLE',
        'swagger_object': 'ApiVersion'
    },
    'workspaces': {
        'key_properties': ['id'],
        'replication_method': 'FULL_TABLE',
        'swagger_object': 'Workspace'
    },
    'query_history': {
        'path': 'queries/run/json?limit=10000&apply_formatting=false&apply_vis=false&cache=false&force_production=true&server_table_calcs=false',
        'key_properties': ['query_id', 'history_created_date', 'dims_hash_key'],
        'replication_method': 'FULL_TABLE',
        'method': 'POST',
        'body': {
            'model': 'i__looker',
            'view': 'history',
            'fields': [
                'query.id',
                'history.created_date',
                'query.model',
                'query.view',
                'space.id',
                'look.id',
                'dashboard.id',
                'user.id',
                'history.query_run_count',
                'history.total_runtime'
            ],
            'filters': {
                'query.model': '-EMPTY',
                'history.runtime': 'NOT NULL',
                'history.created_date': '1 week',
                'user.is_looker': 'No'
            },
            'sorts': [
                'query.id',
                'history.created_date'
            ]
        }
    }
}

# De-nest children nodes for Discovery mode
def flatten_streams():
    flat_streams = {}
    # Loop through parents
    for stream_name, endpoint_config in STREAMS.items():
        flat_streams[stream_name] = {
            'key_properties': endpoint_config.get('key_properties'),
            'replication_method': endpoint_config.get('replication_method'),
            'replication_keys': endpoint_config.get('replication_keys'),
            'swagger_object': endpoint_config.get('swagger_object')
        }
        # Loop through children
        children = endpoint_config.get('children')
        if children:
            for child_stream_name, child_endpoint_config in children.items():
                flat_streams[child_stream_name] = {
                    'key_properties': child_endpoint_config.get('key_properties'),
                    'replication_method': child_endpoint_config.get('replication_method'),
                    'replication_keys': child_endpoint_config.get('replication_keys'),
                    'swagger_object': child_endpoint_config.get('swagger_object')
                }
                # Loop through grand-children
                grandchildren = child_endpoint_config.get('children')
                if grandchildren:
                    for grandchild_stream_name, grandchild_endpoint_config in \
                        grandchildren.items():
                        flat_streams[grandchild_stream_name] = {
                            'key_properties': grandchild_endpoint_config.get('key_properties'),
                            'replication_method': grandchild_endpoint_config.get\
                                ('replication_method'),
                            'replication_keys': grandchild_endpoint_config.get('replication_keys'),
                            'swagger_object': grandchild_endpoint_config.get('swagger_object')
                        }
    return flat_streams
