import requests
from constants import opencage_key, opencage_api_url


def get_location(latitude: float, longitude: float, lang='en', pretty=0, no_annotations=1):
    response = requests.get(opencage_api_url, params={
        'key': opencage_key,
        'q': f'{latitude},{longitude}',
        'language': lang,
        'pretty': pretty,
        'no_annotations': no_annotations,
        'roadinfo': 1
    })
    if response.status_code == 200:
        result = response.json()
        location = result['results'][0]['components']

        if location.get('country', '') != 'Украина':
            return 0
        ret = list()
        ret.append(location.get('state'))
        if location.get('city'):
            ret.append(location.get('city'))
        else:
            ret.append(location.get('county'))
            ret.append(location.get('hamlet'))
        ret.append(location.get('road'))

        ret = filter(lambda x: x is not None, ret)
        ret = ', '.join(ret)
        if not ret:
            return
        return ret
    else:
        return
        # raise ValueError(response.text)
