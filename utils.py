def get_all_objects_in_collection(collection):
    """Recursively get all objects in the given collection and its children."""
    all_objects = list(collection.objects)
    for child_collection in collection.children:
        all_objects.extend(get_all_objects_in_collection(child_collection))
    return all_objects