from functools import wraps
from src.config import SEASON, WEEKS_TOTAL


def load_and_cache():
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get the function name of the function that is being decorated
            func_name = func.__name__
            prop_name = func_name.replace('get_', '')

            # Get the cache file name
            cache_file = '.'.join([prop_name, str(SEASON), 'json'])

            # Get the instance of the class (self)
            instance = args[0]

            # Check if we need to force refresh
            force_refresh = kwargs.get('force_refresh', False)
            
            # When force_refresh is True, we need to fetch the data and store it in cache
            if force_refresh:
                data = func(*args, **kwargs)
                instance.cache_manager.write_to_cache(cache_file, data)

            # When force_refresh is False, we need to check if the data is in class property or cache else fetch it
            else: 
                # Try to get data from class property
                data = getattr(instance, prop_name, None)
                
                # If data is not in class property, try to get it from cache
                if data is None:
                    data = instance.cache_manager.get_from_cache(cache_file)
            
                # If data is not in cache fetch it and store it in cache
                if data is None:
                    data = func(*args, **kwargs)
                    instance.cache_manager.write_to_cache(cache_file, data)
            
            # Set the class property to hold the data
            setattr(instance, prop_name, data)

            return data
        return wrapper
    return decorator

def update_and_cache(prop_name):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get the instance of the class (self)
            instance = args[0]

            # Get the cache file name
            cache_file = '.'.join([prop_name, str(SEASON), 'json'])

            # Call the function
            data_to_return = func(*args, **kwargs)

            # Get the data from the class property
            data_to_cache = getattr(instance, prop_name, None)

            # Update the cache
            instance.cache_manager.write_to_cache(cache_file, data_to_cache)

            return data_to_return
        return wrapper
    return decorator
