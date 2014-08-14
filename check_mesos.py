#!/usr/bin/env python
import nagiosplugin
import urllib2
import argparse
import logging
import re

INFINITY = float('inf')
HEALTHY = 1
UNHEALTHY = -1

try:
  from urllib2 import *
except ImportError:
  from urllib.request import *
  from urllib.error import HTTPError

try:
  import json
except ImportError:
  import simplejson as json

class MesosMaster(nagiosplugin.Resource):
  def __init__(self, baseuri, frameworks):
    self.baseuri = baseuri
    self.frameworks = frameworks

  def probe(self):
    logging.info('Base URI is %s', self.baseuri)
    try:
      response = urlopen(self.baseuri + '/health')
      logging.debug('Response from %s is %s', response.geturl(), response)
      if response.getcode() in [200, 204]:
        yield nagiosplugin.Metric('master health', HEALTHY)
      else:
        yield nagiosplugin.Metric('master health', UNHEALTHY)
    except HTTPError, e:
      logging.debug('HTTP error %s', e)
      yield nagiosplugin.Metric('master health', UNHEALTHY)
    
    response = urlopen(self.baseuri + '/master/state.json')
    logging.debug('Response from %s is %s', response.geturl(), response)
    state = json.load(response)
    
    has_leader = len(state.get('leader', '')) > 0
    
    yield nagiosplugin.Metric('active slaves', state['activated_slaves'])
    yield nagiosplugin.Metric('active leader', 1 if has_leader else 0)

    for framework_regex in self.frameworks:
      framework = None
      for candidate in state['frameworks']:
        if re.search(framework_regex, candidate['name']) is not None:
          framework = candidate
      
      unregistered_time = INFINITY
      
      if framework is not None:
        unregistered_time = framework['unregistered_time']
        if not framework['active'] and unregistered_time == 0:
          unregistered_time = INFINITY
      yield nagiosplugin.Metric('framework ' + framework_regex, unregistered_time, context='framework')
      

@nagiosplugin.guarded
def main():
  argp = argparse.ArgumentParser()
  argp.add_argument('-H', '--host', required=True,
                    help='The hostname of a Mesos master to check')
  argp.add_argument('-P', '--port', default=5050,
                    help='The Mesos master HTTP port - defaults to 5050')
  argp.add_argument('-n', '--slaves', default=1,
                    help='The minimum number of slaves the cluster must be running')
  argp.add_argument('-F', '--framework', default=[], action='append',
                    help='Check that a framework is registered matching the given regex, may be specified multiple times')
  argp.add_argument('-v', '--verbose', action='count', default=0,
                    help='increase output verbosity (use up to 3 times)')
  
  args = argp.parse_args()
  
  unhealthy_range = nagiosplugin.Range('%d:%d' % (HEALTHY - 1, HEALTHY + 1))
  slave_range = nagiosplugin.Range('%s:' % (args.slaves,))
  
  check = nagiosplugin.Check(
              MesosMaster('http://%s:%d' % (args.host, args.port), args.framework),
              nagiosplugin.ScalarContext('master health', unhealthy_range, unhealthy_range),
              nagiosplugin.ScalarContext('active slaves', slave_range, slave_range),
              nagiosplugin.ScalarContext('active leader', '1:1', '1:1'),
              nagiosplugin.ScalarContext('framework', '0:0', '0:0'))
  check.main(verbose=args.verbose)

if __name__ == '__main__':
  main()
