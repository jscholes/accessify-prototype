import os.path

import ujson as json


class WebAPIClient:
    def search(self, query, search_type):
        # This code won't last for long
        module_dir, _ = os.path.split(__file__)
        json_path = os.path.join(module_dir, 'searchresponses')
        filename = '{0}-{1}.json'.format(search_type, query.lower().replace(' ', '_'))
        try:
            with open(os.path.join(json_path, filename), 'r', encoding='utf-8') as f:
                data = json.load(f)
        except (FileNotFoundError, ValueError):
            return {} # No results
        return data

