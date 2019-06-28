from graphql import is_object_type, is_introspection_type, extend_schema, parse, is_scalar_type, is_enum_type, \
    get_named_type, is_non_null_type, GraphQLNonNull, is_list_type, GraphQLList, is_interface_type


def add_query_and_mutation_types(_schema):
    make = 'type Query ' \
           'type Mutation'
    _schema = add_to_schema(_schema, make)
    return _schema


def get_reverse_field_name(type_name, field_name):
    """
    Create '_YFromX' based on a type and a field.
    :param type_name: Name of original type
    :param field_name: Name of original field
    :return: _YFromX
    """
    return '_{0}From{1}'.format(field_name, capitalize(type_name))


def get_name_input_to_create(type_name):
    """
    Create '_InputToCreateX' based on a type name.
    :param type_name: Name of type
    :return: _InputToCreateX
    """
    return '_InputToCreate{0}'.format(capitalize(type_name))


def get_filter_name(type_name):
    """
    Create '_InputToFilterX' based on a type name.
    :param type_name: Name of type
    :return: _InputToFilterX
    """
    return '_InputToFilter{0}'.format(capitalize(type_name))


def get_name_interface_input_to_create(type_name):
    """
    Create name of field for creating implementing type of interface.
    'createX' based on type name.
    :param type_name: Name of type
    :return: createX
    """
    return 'create{0}'.format(capitalize(type_name))


def get_name_input_to_update(type_name):
    """
    Create 'InputToUpdateX' based on a type and a field.
    :param type_name: Name of type
    :return: _InputToUpdateX
    """
    return '_InputToUpdate{0}'.format(capitalize(type_name))


def get_name_input_to_connect(type_name):
    """
    Create 'InputToConnectX' based on a type and a field.
    :param type_name: Name of type
    :return: _InputToConnectX
    """
    return '_InputToConnect{0}'.format(capitalize(type_name))


def capitalize(string):
    """
    Make the first letter of string upper case.
    :param string:
    :return:
    """
    return string[0].upper() + string[1:]


def decapitalize(string):
    """
    Make the first letter of string lower case.
    :param string:
    :return:
    """
    return string[0].lower() + string[1:]


def add_to_schema(_schema, _make):
    try:
        _schema = extend_schema(_schema, parse(_make))
    except TypeError as e:
        print(e)
    except SyntaxError as e:
        print(e)

    return _schema


def is_schema_defined_object_type(_type):
    """
    Returns true iff the provided type is schema-defined object type (i.e., not introspection type, mutation, or query).
    :param _type:
    :return:
    """
    if not is_object_type(_type) or is_introspection_type(_type) or _type.name == 'Mutation' or _type.name == 'Query':
        return False
    return True


def is_generated_object_type(_type):
    """
    Returns true iff the provided type is an automatically generated object type.
    :param _type:
    :return:
    """
    return is_schema_defined_object_type(_type) and _type.name.startsWith('_')


def add_id_to_object_types(_schema):
    """
    Extend all object types in the schema with an ID field.
    :param _schema:
    :return:
    """
    for type_name, _type in _schema.type_map.items():
        if is_schema_defined_object_type(_type) and type_name[0] != '_':
            _schema = extend_schema(_schema, parse('extend type {0} {{ id: ID! }}'.format(type_name)))
    return _schema


def add_id_to_interface_types(_schema):
    """
    Extend all interface types in the schema with an ID field.
    :param _schema:
    :return:
    """
    for type_name, _type in _schema.type_map.items():
        if is_interface_type(_type) and type_name[0] != '_':
            _schema = extend_schema(_schema, parse('extend interface {0} {{ id: ID! }}'.format(type_name)))
    return _schema


def copy_wrapper_structure(_type, _original):
    """
    Copy the wrapper structure from _original to _type.
    :param _type: GraphQL type
    :param _original: Wrapped GraphQL type
    :return: Wrapped GraphQL type
    """
    wrapped_type = get_named_type(_type)
    # A, A!, [A!], [A]!, [A!]!
    wrappers = []
    if is_non_null_type(_original):
        wrappers.insert(0, GraphQLNonNull)
        _original = _original.of_type
    if is_list_type(_original):
        wrappers.insert(0, GraphQLList)
        _original = _original.of_type
    if is_non_null_type(_original):
        wrappers.insert(0, GraphQLNonNull)
        _original = _original.of_type
    if is_list_type(_original):
        wrappers.insert(0, GraphQLList)
        _original = _original.of_type

    for i in wrappers:
        wrapped_type = i(wrapped_type)

    return wrapped_type


def add_reverse_edges(_schema):
    """
    Add reverse edges all edges of object types.
    :param _schema: schema
    :return: updated schema
    """
    for type_name, _type in _schema.type_map.items():
        if is_schema_defined_object_type(_type):
            for field_name, field_type in _type.fields.items():
                inner_field_type = get_named_type(field_type.type)
                if is_scalar_type(inner_field_type) or is_enum_type(inner_field_type):
                    continue

                # Reverse edge
                edge_from = get_named_type(field_type.type)
                edge_name = get_reverse_field_name(type_name, field_name)
                edge_to = GraphQLList(_type)

                if is_interface_type(edge_from):
                    for implementing_type in _schema.get_possible_types(edge_from):
                        make = 'extend type {0} {{ {1}: {2} }}'.format(implementing_type, edge_name, edge_to)
                        _schema = add_to_schema(_schema, make)
                else:
                    make = 'extend type {0} {{ {1}: {2} }}'.format(edge_from, edge_name, edge_to)
                    _schema = add_to_schema(_schema, make)

    return _schema


def add_create_and_connect_input_types(_schema):
    """
    Add input types for creating and connecting objects.
    :param _schema: GraphQL schema
    :return: Extended GraphQL schema
    """

    # Create all input types
    for type_name, _type in _schema.type_map.items():
        if is_schema_defined_object_type(_type) and type_name[0] != '_':
            create = get_name_input_to_create(type_name)
            connect = get_name_input_to_connect(type_name)
            # add create
            make = 'input {0}'.format(create)
            _schema = add_to_schema(_schema, make)
            # add connect
            make = 'input {0} {{ connect: ID, create: {1} }}'.format(connect, create)
            _schema = add_to_schema(_schema, make)
        elif is_interface_type(_type):
            # add connect input type for interface
            connect = get_name_input_to_connect(type_name)
            make = 'input {0} {{ connect: ID }}'.format(connect)
            _schema = add_to_schema(_schema, make)


    # Add fields to create input type
    for type_name, _type in _schema.type_map.items():
        if is_schema_defined_object_type(_type) and type_name[0] != '_':
            create = get_name_input_to_create(type_name)

            for field_name, field_type in _type.fields.items():
                if field_name == 'id' or field_name[0] == '_': # skip reverse edges
                    continue

                inner_field_type = get_named_type(field_type.type)
                if is_scalar_type(inner_field_type) or is_enum_type(inner_field_type):
                    # inner field type is scalar or enum, use directly
                    make = 'extend input {0} {{ {1}: {2} }}'.format(create, field_name, field_type.type)
                    _schema = add_to_schema(_schema, make)
                else:
                    if is_interface_type(inner_field_type):
                        connect = get_name_input_to_connect(inner_field_type.name)
                        # add create, add fields for all implementing types
                        for implementing_type in _schema.get_possible_types(inner_field_type):
                            create_field = get_name_interface_input_to_create(implementing_type.name)
                            create_type = get_name_input_to_connect(implementing_type.name)
                            make = 'extend input {0} {{ {1} : {2} }}'.format(connect, create_field, create_type)
                            _schema = add_to_schema(_schema, make)
                    else:
                        # get inner named type of type field
                        input_to_connect = get_name_input_to_connect(inner_field_type.name)
                        # add create field
                        wrapped_field_type = copy_wrapper_structure(_schema.get_type(input_to_connect), field_type.type)
                        make = 'extend input {0} {{ {1}: {2} }}'.format(create, field_name, wrapped_field_type)
                        _schema = add_to_schema(_schema, make)

    return _schema


def add_update_input_types(_schema):
    """
    Add update types for creating and connecting objects.
    :param _schema: GraphQL schema
    :return: Extended GraphQL schema
    """

    # Add fields to create input type
    for type_name, _type in _schema.type_map.items():
        if is_schema_defined_object_type(_type) and type_name[0] != '_':
            update = get_name_input_to_update(type_name)
            # add create
            make = 'input {0}'.format(update)
            _schema = add_to_schema(_schema, make)

            for field_name, field_type in _type.fields.items():
                if field_name == 'id' or field_name[0] == '_':
                    continue

                f_type = field_type.type
                # remove required
                if is_non_null_type(field_type.type):
                    f_type = get_named_type(field_type.type)

                inner_field_type = get_named_type(f_type)
                if is_scalar_type(inner_field_type) or is_enum_type(inner_field_type):
                    # inner field type is scalar or enum, use directly
                    make = 'extend input {0} {{ {1}: {2} }}'.format(update, field_name, f_type)
                    _schema = add_to_schema(_schema, make)
                else:
                    # get inner named type of type field
                    input_to_connect = get_name_input_to_connect(inner_field_type.name)
                    # add create field
                    wrapped_field_type = copy_wrapper_structure(_schema.get_type(input_to_connect), f_type)
                    make = 'extend input {0} {{ {1}: {2} }}'.format(update, field_name, wrapped_field_type)
                    _schema = add_to_schema(_schema, make)

    return _schema


def add_get_queries(_schema):
    # Create queries for object types
    for type_name, _type in _schema.type_map.items():
        if is_schema_defined_object_type(_type) and type_name[0] != '_':
            get = decapitalize(type_name)
            make = 'extend type Query {{ {0}(id:ID!): {1} }}'.format(get, type_name)
            _schema = add_to_schema(_schema, make)
        elif is_interface_type(_type):
            get = decapitalize(type_name)
            make = 'extend type Query {{ {0}(id:ID!): {1} }}'.format(get, type_name)
            _schema = add_to_schema(_schema, make)
    return _schema


def add_list_of_types(_schema):
    """
    Add list type to represent lists of all types and support paging.
    :param _schema:
    :return:
    """
    # Create queries for object types
    for type_name, _type in _schema.type_map.items():
        if is_schema_defined_object_type(_type) and type_name[0] != '_':
            make = 'type _ListOf{0}s {{ ' \
                   'totalCount: Int ' \
                   'isEndOfWholeList: Boolean ' \
                   'content: [{0}] }}'.format(type_name)
            _schema = add_to_schema(_schema, make)
        elif is_interface_type(_type):
            make = 'type _ListOf{0}s {{ ' \
                   'totalCount: Int ' \
                   'isEndOfWholeList: Boolean ' \
                   'content: [{0}] }}'.format(type_name)
            _schema = add_to_schema(_schema, make)
    return _schema


def add_list_queries(_schema):
    # Create queries for object types
    for type_name, _type in _schema.type_map.items():
        if is_schema_defined_object_type(_type) and type_name[0] != '_':
            _list = 'listOf{0}s'.format(capitalize(type_name))
            make = 'extend type Query {{ ' \
                   '{0}(first:Int=10, after:ID="", filter:_FilterFor{1}): _ListOf{1}s }}'\
                .format(_list, type_name)
            _schema = add_to_schema(_schema, make)
        elif is_interface_type(_type):
            _list = 'listOf{0}s'.format(capitalize(type_name))
            make = 'extend type Query {{ ' \
                   '{0}(first:Int=10, after:ID="", filter:_FilterFor{1}): _ListOf{1}s }}'\
                .format(_list, type_name)
            _schema = add_to_schema(_schema, make)
    return _schema


def add_scalar_filters(_schema):
    """
    Add filter inputs for built-in scalars following the Hasura style.
    :param _schema: schema
    :return: Updated schema
    """
    # Numeric
    scalars = ['Int', 'Float']
    for scalar in scalars:
        make = 'input _{0}Filter {{' \
               '_eq: {0} ' \
               '_neq: {0} ' \
               '_gt: {0} ' \
               '_egt: {0} ' \
               '_lt: {0} ' \
               '_elt: {0} ' \
               '_in: [{0}] ' \
               '_nin: [{0}] ' \
               '}}'.format(scalar)
        _schema = add_to_schema(_schema, make)

    # String
    make = 'input _{0}Filter {{' \
           '_eq: {0} ' \
           '_neq: {0} ' \
           '_gt: {0} ' \
           '_egt: {0} ' \
           '_lt: {0} ' \
           '_elt: {0} ' \
           '_in: [{0}] ' \
           '_nin: [{0}] ' \
           '_like: String ' \
           '_ilike: String ' \
           '_nlike: String ' \
           '_nilike: String ' \
           '}}'.format('String')
    _schema = add_to_schema(_schema, make)

    # Boolean
    make = 'input _{0}Filter {{' \
           '_eq: {0} ' \
           '_neq: {0} ' \
           '}}'.format('Boolean')
    _schema = add_to_schema(_schema, make)

    # ID and schema-defined scalars
    for scalar_name, scalar in _schema.type_map.items():
        if not is_scalar_type(scalar) or scalar_name in ['Int', 'Float', 'String', 'Boolean']:
            continue

        make = 'input _{0}Filter {{' \
               '_eq: {0} ' \
               '_neq: {0} ' \
               '_in: [{0}] ' \
               '_nin: [{0}] ' \
               '}}'.format(scalar_name)
        _schema = add_to_schema(_schema, make)

    return _schema


def add_type_filters(_schema):
    """
    Add filter inputs for built-in scalars following the Hasura style.
    :param _schema: schema
    :return: Updated schema
    """
    for type_name, _type in _schema.type_map.items():
        if (is_schema_defined_object_type(_type) or is_interface_type(_type)) and type_name[0] != '_':
            make = 'input _FilterFor{0}'.format(type_name)
            _schema = add_to_schema(_schema, make)

            make = 'extend input _FilterFor{0} {{' \
                   '_and: [_FilterFor{0}] ' \
                   '_or: [_FilterFor{0}] ' \
                   '_not: _FilterFor{0}' \
                   '}}'.format(type_name)
            _schema = add_to_schema(_schema, make)

            for field_name, field_type in _type.fields.items():
                if field_name[0] == '_':
                    continue

                f_type = field_type.type
                # remove required
                if is_non_null_type(field_type.type):
                    f_type = get_named_type(field_type.type)

                if is_list_type(f_type):
                    # Unknown how filters would apply for lists, skip.
                    continue

                inner_field_type = get_named_type(f_type)
                if is_scalar_type(inner_field_type) or is_enum_type(inner_field_type):
                    make = 'extend input _FilterFor{0} {{ {1}: _{2}Filter }}'.format(type_name, field_name, f_type)
                    _schema = add_to_schema(_schema, make)

    return _schema


def add_enum_filters(_schema):
    """
    Add filter inputs for enums following the Hasura style.
    :param _schema: schema
    :return: Updated schema
    """
    for enum_name, enum in _schema.type_map.items():
        if not is_enum_type(enum) or is_introspection_type(enum):
            continue

        make = 'input _{0}Filter {{' \
               '_eq: {0} ' \
               '_neq: {0} ' \
               '_in: [{0}] ' \
               '_nin: [{0}] ' \
               '}}'.format(enum_name)
        _schema = add_to_schema(_schema, make)

    return _schema


def add_create_mutations(_schema):
    """
    Add mutations for creating object types.
    :param _schema: schema
    :return: schema
    """
    for type_name, _type in _schema.type_map.items():
        if is_schema_defined_object_type(_type) and type_name[0] != '_':
            create = 'create{0}'.format(capitalize(type_name))
            input_to_create = get_name_input_to_create(type_name)
            make = 'extend type Mutation {{ {0}(data: {1}!): {2} }}'.format(create, input_to_create, type_name)
            _schema = add_to_schema(_schema, make)

    return _schema


def add_update_mutations(_schema):
    """
    Add mutations for updating object types.
    :param _schema: schema
    :return: schema
    """
    for type_name, _type in _schema.type_map.items():
        if is_schema_defined_object_type(_type) and type_name[0] != '_':
            update = 'update{0}'.format(capitalize(type_name))
            input_to_update = get_name_input_to_update(type_name)
            make = 'extend type Mutation {{ {0}(id: ID!, data: {1}!): {2} }}'.format(update, input_to_update, type_name)
            _schema = add_to_schema(_schema, make)

    return _schema


def add_delete_mutations(_schema):
    """
    Add mutations for deleting object types.
    :param _schema: schema
    :return: schema
    """
    for type_name, _type in _schema.type_map.items():
        if is_schema_defined_object_type(_type) and type_name[0] != '_':
            delete = 'delete{0}'.format(capitalize(type_name))
            make = 'extend type Mutation {{ {0}(id: ID!): {1} }}'.format(delete, type_name)
            _schema = add_to_schema(_schema, make)

    return _schema