#!/usr/bin/env python
import nagiosplugin
import argparse
import logging
import re
import requests
from urlparse import urlparse

INFINITY = float('inf')
HEALTHY = 1
UNHEALTHY = -1
REQUEST_TIMEOUT = 10

log = logging.getLogger("nagiosplugin")


class MesosMaster(nagiosplugin.Resource):
  def __init__(self, host, port, username, password, frameworks):
    parsed_host = urlparse(host)
    host = host if parsed_host.scheme else 'http://' + host
    self.baseuri = '%s:%d' % (host, port)
    self.frameworks = frameworks
    self.username = username
    self.password = password

  def build_redirection(self, master_uri, location):
    original = urlparse(master_uri)
    redirect = urlparse(location)
    if redirect.scheme == '':
      return original.scheme + ':' + location
    else: # version <0.23
      return location

  def probe(self):
    master_uri=self.baseuri
    log.debug('Looking at %s for redirect', master_uri)

    try:
      if self.username == "":
        response = requests.head(master_uri + '/master/redirect', timeout=REQUEST_TIMEOUT, allow_redirects=False)
      else:
        response = requests.head(master_uri + '/master/redirect', timeout=REQUEST_TIMEOUT, allow_redirects=False, auth=(self.username, self.password))
      if response.status_code != 307:
        yield nagiosplugin.Metric('leader redirect', UNHEALTHY)
      log.info('Redirect response is %s', response)
      master_uri = self.build_redirection(master_uri, response.headers['Location'])
      # yield the leader redirect later, the summary takes the first check which we want to be 'master health'
    except requests.exceptions.RequestException, e:
      log.error('leader redirect %s', e)
      yield nagiosplugin.Metric('leader redirect', UNHEALTHY)
      return

    log.debug('Base URI is redirected to %s', master_uri)

    if self.username == "":
      response = requests.get(master_uri + '/health', timeout=REQUEST_TIMEOUT)
    else:
      response = requests.get(master_uri + '/health', timeout=REQUEST_TIMEOUT, auth=(self.username, self.password))
    log.info('Response from %s is %s', response.request.url, response)
    if response.status_code in [200, 204]:
      yield nagiosplugin.Metric('master health', HEALTHY)
    else:
      yield nagiosplugin.Metric('master health', UNHEALTHY)

    if self.username == "":
      response = requests.get(master_uri + '/metrics/snapshot', timeout=REQUEST_TIMEOUT)
    else:
      response = requests.get(master_uri + '/metrics/snapshot', timeout=REQUEST_TIMEOUT, auth=(self.username, self.password))
    log.info('Response from %s is %s', response.request.url, response)
    if response.encoding is None:
      response.encoding = "UTF8"
    state = response.json()

    yield nagiosplugin.Metric('active slaves', state['master/slaves_active'])
    yield nagiosplugin.Metric('active leader', state['master/elected'])
    yield nagiosplugin.Metric('active frameworks', state['master/frameworks_active'])

    # now we can yield the redirect status, from above
    yield nagiosplugin.Metric('leader redirect', HEALTHY)

@nagiosplugin.guarded
def main():
  argp = argparse.ArgumentParser()
  argp.add_argument('-H', '--host', required=True,
                    help='The hostname of a Mesos master to check')
  argp.add_argument('-P', '--port', default=5050,
                    help='The Mesos master HTTP port - defaults to 5050')
  argp.add_argument('-u', '--username', default="",
                    help='The optional username if auth is enabled')
  argp.add_argument('-p', '--password', default="",
                    help='The optional password if auth is enabled')
  argp.add_argument('-n', '--slaves', default=1,
                    help='The minimum number of slaves the cluster must be running')
  argp.add_argument('-F', '--frameworks', default=1,
                    help='The minimum number of frameworks that must be active')
  argp.add_argument('-v', '--verbose', action='count', default=0,
                    help='increase output verbosity (use up to 3 times)')

  args = argp.parse_args()

  unhealthy_range = nagiosplugin.Range('%d:%d' % (HEALTHY - 1, HEALTHY + 1))
  slave_range = nagiosplugin.Range('%s:' % (args.slaves,))
  framework_range = nagiosplugin.Range('%s:' % (args.frameworks,))

  check = nagiosplugin.Check(
    MesosMaster(args.host, args.port,args.username, args.password, args.frameworks),
    nagiosplugin.ScalarContext('leader redirect', unhealthy_range, unhealthy_range),
    nagiosplugin.ScalarContext('master health', unhealthy_range, unhealthy_range),
    nagiosplugin.ScalarContext('active slaves', slave_range, slave_range),
    nagiosplugin.ScalarContext('active leader', '1:1', '1:1'),
    nagiosplugin.ScalarContext('active frameworks', framework_range, framework_range))
  check.main(verbose=args.verbose)

if __name__ == '__main__':
  main()