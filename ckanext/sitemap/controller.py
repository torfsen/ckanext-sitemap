'''
Controller for sitemap
'''
import logging

from ckan.lib.base import BaseController
from ckan.model import Session, Package
from ckan.lib.helpers import url_for
from lxml import etree
from pylons import config, response
from pylons.decorators.cache import beaker_cache

SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"

XHTML_NS = "http://www.w3.org/1999/xhtml"

log = logging.getLogger(__name__)

locales = config.get('ckan.locales_offered', '').split()

default_locale = config.get('ckan.locale_default', 'en')


def locale_urls_for(*args, **kwargs):
    '''
    Create URLs for all supported locales.

    Works like ``ckan.lib.helpers.url_for``, but instead of returning a
    single URL returns a dict that maps each offered locale to the
    corresponding URL.
    '''
    # Omit locale code in default locale
    urls = {default_locale: url_for(*args, **kwargs)}
    for locale in locales:
        if locale != default_locale:
            urls[locale] = url_for(*args, locale=locale, **kwargs)
    return urls


class SitemapController(BaseController):

    @beaker_cache(expire=3600*24, type="dbm", invalidate_on_startup=True)
    def _render_sitemap(self):
        root = etree.Element("urlset", nsmap={None: SITEMAP_NS, 'xhtml': XHTML_NS})
        pkgs = Session.query(Package).filter(Package.type=='dataset').filter(Package.private!=True).\
            filter(Package.state=='active').all()
        for pkg in pkgs:
            locale_urls = locale_urls_for(controller='package', action='read',
                                          id=pkg.name, qualified=True)
            lastmod_text = pkg.metadata_modified.strftime('%Y-%m-%d')
            # We need to create a separate <url> element for each locale's URL,
            # see https://support.google.com/webmasters/answer/2620865
            for main_locale, main_url in locale_urls.iteritems():
                url = etree.SubElement(root, 'url')
                loc = etree.SubElement(url, 'loc')
                loc.text = main_url
                lastmod = etree.SubElement(url, 'lastmod')
                lastmod.text = lastmod_text
                for locale, locale_url in locale_urls.iteritems():
                    attrib = {
                        "rel": "alternate",
                        "hreflang": locale,
                        "href": locale_url,
                    }
                    etree.SubElement(url, '{http://www.w3.org/1999/xhtml}link',
                                     attrib)
        response.headers['Content-type'] = 'text/xml'
        return etree.tostring(root, pretty_print=True)

    def view(self):
        return self._render_sitemap()

