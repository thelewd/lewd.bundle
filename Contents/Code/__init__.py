from datetime import datetime
import re

BASE_URL = 'http://amethyst:6969/api'

LEWD_SCENE = '%s/scenes/%%s/?format=json' % (BASE_URL)
LEWD_POSTERS = '%s/scenes/%%s/posters/?format=json' % (BASE_URL)
LEWD_BACKDROPS = '%s/scenes/%%s/backdrops/?format=json' % (BASE_URL)
LEWD_STUDIOS = '%s/studios/%%s/?format=json' % (BASE_URL)
LEWD_PEOPLE = '%s/people/%%s/?format=json' % (BASE_URL)

POSTER_LIMIT = 3
BACKDROP_LIMIT = 3

def Start():
    # HTTP.CacheTime = CACHE_1DAY
    Log('The Lews Database Agent Initiated')


class LewdAgent(Agent.Movies):

    name = "Lewd"
    languages = [Locale.Language.English]
    primary_provider = True
    accepts_from = ['com.plexapp.agents.localmedia']

    def search(self, results, media, lang):

        # we require we look up the scene using the id at the end of the filename
        # maybe in future a search feature can be implemented
        # we use a regex expression to extract this id and look it up on the api
        title = re.findall(r'\d+', media.name)[-1]

        url = LEWD_SCENE % (title)
        res = JSON.ObjectFromURL(url, sleep=2.0)

        pub_date = datetime.strptime(res['pub_date'], '%Y-%m-%d')

        results.Append(MetadataSearchResult(
            id=str(res['id']),
            name=res['title'],
            year=pub_date.year,
            score=100,
            lang=lang
        ))

    def update(self, metadata, media, lang):

        try:
            # create scene info look up url
            url = LEWD_SCENE % (metadata.id)

            # get info about scene
            info = JSON.ObjectFromURL(url, sleep=2.0)

            # title
            if 'title' in info and info['title'] is not None:
                metadata.title = info['title']

            # summary
            if 'description' in info and info['description'] is not None:
                metadata.summary = info['description']

            # year
            if 'pub_date' in info and info['pub_date'] is not None:
                pub_date = datetime.strptime(info['pub_date'], '%Y-%m-%d')
                metadata.year = pub_date.year
                metadata.originally_available_at = pub_date

            # studios as collection
            if 'studios' in info and info['studios'] is not None:
                metadata.collections.clear()
                
                for s in info['studios']:
                    url = LEWD_STUDIOS % (s)
                    res = JSON.ObjectFromURL(url, sleep=2.0)
                        
                    if res['primary']:
                        metadata.studio = res['name']
                    else:
                        metadata.collections.add(res['name'])
                        

            # roles
            if 'people' in info and info['people'] is not None:
                metadata.roles.clear()
                for p in info['people']:
                    url = LEWD_PEOPLE % (p)
                    res = JSON.ObjectFromURL(url, sleep=2.0)
                    role = metadata.roles.new()
                    role.name = res['name']
                    role.photo = res['photo']


            # duh
            metadata.content_rating = 'R'

            # posters
            # create posters look up url
            url = LEWD_POSTERS % (metadata.id)
            res = JSON.ObjectFromURL(url, sleep=2.0)['results']

            if res:
                valid_names = list()
                # sort the images by placing the primary image first
                for i, p in enumerate(sorted(res, key=lambda k: k['primary'], reverse=True)):
                    if i > POSTER_LIMIT:
                        break

                    poster_url = p['image']
                    valid_names.append(poster_url)
                    
                    if poster_url not in metadata.posters:
                        try:
                            metadata.posters[poster_url] = Proxy.Preview(
                                HTTP.Request(poster_url).content, sort_order=i+1)
                        except Exception as e:
                            Log.Error('Failed to set poster %s on %s',
                                      poster_url, metadata.id)

            metadata.posters.validate_keys(valid_names)

            # backdrops
            # create backdrops look up url
            url = LEWD_BACKDROPS % (metadata.id)
            res = JSON.ObjectFromURL(url, sleep=2.0)['results']

            if res:
                valid_names = list()
                # sort the images by plaing the primary image first
                for i, b in enumerate(sorted(res, key=lambda k: k['primary'], reverse=True)):
                    if i > BACKDROP_LIMIT:
                        break

                    backdrop_url = b['image']
                    valid_names.append(backdrop_url)

                    if backdrop_url not in metadata.art:
                        try:
                            metadata.art[backdrop_url] = Proxy.Preview(
                                HTTP.Request(backdrop_url).content, sort_order=i+1)
                        except Exception as e:
                            Log.Error('Failed to set backdrop %s on %s',
                                      poster_url, metadata.id)

            metadata.art.validate_keys(valid_names)

        except Exception as e:
            Log.Error(
                'Failed to obtain data for item %s (%s) [%s]', metadata.id, url, e.message)
