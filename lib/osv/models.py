# Copyright 2021 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Datastore types."""

import datetime
import enum
import re
import os

from google.cloud import ndb
from google.protobuf import timestamp_pb2

# pylint: disable=relative-beyond-top-level
from . import bug
from . import ecosystems
from . import semver_index
from . import sources
from . import vulnerability_pb2


def _check_valid_severity(prop, value):
  """Check valid severity."""
  del prop

  if value not in ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL'):
    raise ValueError('Invalid severity: ' + value)


def _check_valid_range_type(prop, value):
  """Check valid range type."""
  del prop

  if value not in ('GIT', 'SEMVER', 'ECOSYSTEM'):
    raise ValueError('Invalid range type: ' + value)


def _check_valid_event_type(prop, value):
  """Check valid event type."""
  del prop

  if value not in ('introduced', 'fixed', 'limit'):
    raise ValueError('Invalid event type: ' + value)


def utcnow():
  """For mocking."""
  return datetime.datetime.utcnow()


class IDCounter(ndb.Model):
  """Counter for ID allocations."""
  # Next ID to allocate.
  next_id = ndb.IntegerProperty()


class AffectedCommit(ndb.Model):
  """AffectedCommit entry."""
  # The main bug ID.
  bug_id = ndb.StringProperty()
  # The commit hash.
  commit = ndb.StringProperty()
  # Project for the bug.
  project = ndb.StringProperty()
  # Ecosystem for the affected commit.
  ecosystem = ndb.StringProperty()
  # Whether or not the bug is public.
  public = ndb.BooleanProperty()


class RegressResult(ndb.Model):
  """Regression results."""
  # The commit hash.
  commit = ndb.StringProperty(default='')
  # Vulnerability summary.
  summary = ndb.TextProperty()
  # Vulnerability details.
  details = ndb.TextProperty()
  # Error (if any).
  error = ndb.StringProperty()
  # OSS-Fuzz issue ID.
  issue_id = ndb.StringProperty()
  # Project for the bug.
  project = ndb.StringProperty()
  # Package ecosystem for the project.
  ecosystem = ndb.StringProperty()
  # Repo URL.
  repo_url = ndb.StringProperty()
  # Severity of the bug.
  severity = ndb.StringProperty(validator=_check_valid_severity)
  # Reference URLs.
  reference_urls = ndb.StringProperty(repeated=True)
  # Source timestamp.
  timestamp = ndb.DateTimeProperty()


class FixResult(ndb.Model):
  """Fix results."""
  # The commit hash.
  commit = ndb.StringProperty(default='')
  # Vulnerability summary.
  summary = ndb.TextProperty()
  # Vulnerability details.
  details = ndb.TextProperty()
  # Error (if any).
  error = ndb.StringProperty()
  # OSS-Fuzz issue ID.
  issue_id = ndb.StringProperty()
  # Project for the bug.
  project = ndb.StringProperty()
  # Package ecosystem for the project.
  ecosystem = ndb.StringProperty()
  # Repo URL.
  repo_url = ndb.StringProperty()
  # Severity of the bug.
  severity = ndb.StringProperty(validator=_check_valid_severity)
  # Reference URLs.
  reference_urls = ndb.StringProperty(repeated=True)
  # Source timestamp.
  timestamp = ndb.DateTimeProperty()


class AffectedRange(ndb.Model):
  """Affected range."""
  # Type of range.
  type = ndb.StringProperty(validator=_check_valid_range_type)
  # Repo URL.
  repo_url = ndb.StringProperty()
  # The regressing commit.
  introduced = ndb.StringProperty()
  # The fix commit.
  fixed = ndb.StringProperty()


class AffectedEvent(ndb.Model):
  """Affected event."""
  type = ndb.StringProperty(validator=_check_valid_event_type)
  value = ndb.StringProperty()


class AffectedRange2(ndb.Model):
  """Affected range."""
  # Type of range.
  type = ndb.StringProperty(validator=_check_valid_range_type)
  # Repo URL.
  repo_url = ndb.StringProperty()
  # Events.
  events = ndb.LocalStructuredProperty(AffectedEvent, repeated=True)


class SourceOfTruth(enum.IntEnum):
  """Source of truth."""
  NONE = 0
  # Internal to OSV (e.g. private OSS-Fuzz bugs).
  INTERNAL = 1
  # Vulnerabilities that are available in a public repo.
  SOURCE_REPO = 2


class Package(ndb.Model):
  """Package."""
  ecosystem = ndb.StringProperty()
  name = ndb.StringProperty()
  purl = ndb.StringProperty()


class AffectedPackage(ndb.Model):
  """Affected packages."""
  # The affected package identifier.
  package = ndb.StructuredProperty(Package)
  # The list of affected ranges.
  ranges = ndb.LocalStructuredProperty(AffectedRange2, repeated=True)
  # The list of explicit affected versions.
  versions = ndb.TextProperty(repeated=True)
  # Database specific metadata.
  database_specific = ndb.JsonProperty()
  # Ecosystem specific metadata.
  ecosystem_specific = ndb.JsonProperty()


class Bug(ndb.Model):
  """Bug entity."""
  OSV_ID_PREFIX = 'OSV-'
  # Very large fake version to use when there is no fix available.
  _NOT_FIXED_SEMVER = '999999.999999.999999'

  # Display ID as used by the source database. The full qualified database that
  # OSV tracks this as may be different.
  db_id = ndb.StringProperty()
  # Other IDs this bug is known as.
  aliases = ndb.StringProperty(repeated=True)
  # Related IDs.
  related = ndb.StringProperty(repeated=True)
  # Status of the bug.
  status = ndb.IntegerProperty()
  # Timestamp when Bug was allocated.
  timestamp = ndb.DateTimeProperty()
  # When the entry was last edited.
  last_modified = ndb.DateTimeProperty()
  # When the entry was withdrawn.
  withdrawn = ndb.DateTimeProperty()
  # The source identifier.
  # For OSS-Fuzz, this oss-fuzz:<ClusterFuzz testcase ID>.
  # For others this is <source>:<path/to/source>.
  source_id = ndb.StringProperty()
  # The main fixed commit (from bisection).
  fixed = ndb.StringProperty(default='')
  # The main regressing commit (from bisection).
  regressed = ndb.StringProperty(default='')
  # All affected ranges. TODO(ochang): To be removed.
  affected_ranges = ndb.StructuredProperty(AffectedRange, repeated=True)
  # List of affected versions.
  affected = ndb.TextProperty(repeated=True)
  # List of normalized versions indexed for fuzzy matching.
  affected_fuzzy = ndb.StringProperty(repeated=True)
  # OSS-Fuzz issue ID.
  issue_id = ndb.StringProperty()
  # Package URL for this package.
  purl = ndb.StringProperty(repeated=True)
  # Project/package name for the bug.
  project = ndb.StringProperty(repeated=True)
  # Package ecosystem for the project.
  ecosystem = ndb.StringProperty(repeated=True)
  # Summary for the bug.
  summary = ndb.TextProperty()
  # Vulnerability details.
  details = ndb.TextProperty()
  # Severity of the bug.
  severity = ndb.StringProperty(validator=_check_valid_severity)
  # Whether or not the bug is public (OSS-Fuzz only).
  public = ndb.BooleanProperty()
  # Reference URL types (dict of url -> type).
  reference_url_types = ndb.JsonProperty()
  # Search indices (auto-populated)
  search_indices = ndb.StringProperty(repeated=True)
  # Whether or not the bug has any affected versions (auto-populated).
  has_affected = ndb.BooleanProperty()
  # Source of truth for this Bug.
  source_of_truth = ndb.IntegerProperty(default=SourceOfTruth.INTERNAL)
  # Whether the bug is fixed (indexed for querying).
  is_fixed = ndb.BooleanProperty()
  # Database specific.
  database_specific = ndb.JsonProperty()
  # Ecosystem specific.
  ecosystem_specific = ndb.JsonProperty()
  # Normalized SEMVER fixed indexes for querying.
  semver_fixed_indexes = ndb.StringProperty(repeated=True)
  # Affected packages and versions.
  affected_packages = ndb.LocalStructuredProperty(
      AffectedPackage, repeated=True)
  # The source of this Bug.
  source = ndb.StringProperty()

  def id(self):
    """Get the bug ID."""
    if self.db_id:
      return self.db_id

    # TODO(ochang): Remove once all existing bugs have IDs migrated.
    if re.match(r'^\d+', self.key.id()):
      return self.OSV_ID_PREFIX + self.key.id()

    return self.key.id()

  @property
  def repo_url(self):
    """Repo URL."""
    for affected_package in self.affected_packages:
      for affected_range in affected_package.ranges:
        if affected_range.repo_url:
          return affected_range.repo_url

    return None

  @classmethod
  def get_by_id(cls, vuln_id, *args, **kwargs):
    """Overridden get_by_id to handle OSV allocated IDs."""
    result = cls.query(cls.db_id == vuln_id).get()
    if result:
      return result

    # TODO(ochang): Remove once all exsting bugs have IDs migrated.
    if vuln_id.startswith(cls.OSV_ID_PREFIX):
      vuln_id = vuln_id[len(cls.OSV_ID_PREFIX):]

    return super().get_by_id(vuln_id, *args, **kwargs)

  def _tokenize(self, value):
    """Tokenize value for indexing."""
    if not value:
      return []

    value_lower = value.lower()
    return re.split(r'\W+', value_lower) + [value_lower]

  def _pre_put_hook(self):
    """Pre-put hook for populating search indices."""
    search_indices = set()

    search_indices.update(self._tokenize(self.id()))

    if self.affected_packages:
      self.project = [
          pkg.package.name for pkg in self.affected_packages if pkg.package.name
      ]
      self.ecosystem = [
          pkg.package.ecosystem
          for pkg in self.affected_packages
          if pkg.package.ecosystem
      ]
      self.purl = [
          pkg.package.purl for pkg in self.affected_packages if pkg.package.purl
      ]

      for project in self.project:
        search_indices.update(self._tokenize(project))

      for ecosystem in self.ecosystem:
        search_indices.update(self._tokenize(ecosystem))

    self.search_indices = sorted(list(search_indices))

    self.affected_fuzzy = []
    self.semver_fixed_indexes = []
    self.has_affected = False
    self.is_fixed = False

    for affected_package in self.affected_packages:
      # Indexes used for querying by exact version.
      self.affected_fuzzy.extend(bug.normalize_tags(affected_package.versions))
      self.has_affected |= bool(affected_package.versions)

      for affected_range in affected_package.ranges:
        fixed_version = None
        for event in affected_range.events:
          # Index used to query by fixed/unfixed.
          if event.type == 'fixed':
            self.is_fixed = True
            fixed_version = event.value

        if affected_range.type == 'SEMVER':
          # Indexes used for querying by semver.
          fixed = fixed_version or self._NOT_FIXED_SEMVER
          self.semver_fixed_indexes.append(semver_index.normalize(fixed))

        self.has_affected |= (affected_range.type in ('SEMVER', 'ECOSYSTEM'))

    if not self.last_modified:
      self.last_modified = utcnow()

    if self.source_id:
      self.source, _ = sources.parse_source_id(self.source_id)

    if not self.source:
      raise ValueError('Source not specified for Bug.')

    if not self.db_id:
      raise ValueError('DB ID not specified for Bug.')

    if not self.key:  # pylint: disable=access-member-before-definition
      source_repo = get_source_repository(self.source)
      if not source_repo:
        raise ValueError(f'Invalid source {self.source}')

      if source_repo.db_prefix and self.db_id.startswith(source_repo.db_prefix):
        key_id = self.db_id
      else:
        key_id = f'{self.source}:{self.db_id}'

      self.key = ndb.Key(Bug, key_id)

  def update_from_vulnerability(self, vulnerability):
    """Set fields from vulnerability. Does not set the ID."""
    self.summary = vulnerability.summary
    self.details = vulnerability.details
    self.reference_url_types = {
        ref.url: vulnerability_pb2.Reference.Type.Name(ref.type)
        for ref in vulnerability.references
    }

    if vulnerability.HasField('modified'):
      self.last_modified = vulnerability.modified.ToDatetime()
    if vulnerability.HasField('published'):
      self.timestamp = vulnerability.published.ToDatetime()
    if vulnerability.HasField('withdrawn'):
      self.withdrawn = vulnerability.withdrawn.ToDatetime()

    if self.affected_packages:
      affected_package = self.affected_packages[0]
    else:
      affected_package = AffectedPackage()
      self.affected_packages.append(affected_package)

    affected_package.package = Package(
        name=vulnerability.package.name,
        ecosystem=vulnerability.package.ecosystem,
        purl=vulnerability.package.purl)

    self.aliases = list(vulnerability.aliases)
    self.related = list(vulnerability.related)

    vuln_dict = sources.vulnerability_to_dict(vulnerability)
    if vulnerability.database_specific:
      affected_package.database_specific = vuln_dict['database_specific']

    if vulnerability.ecosystem_specific:
      affected_package.ecosystem_specific = vuln_dict['ecosystem_specific']

    affected_package.versions = list(vulnerability.affects.versions)
    affected_package.ranges = []
    events_by_type = {}

    for affected_range in vulnerability.affects.ranges:
      events = events_by_type.setdefault(
          (vulnerability_pb2.AffectedRange.Type.Name(
              affected_range.type), affected_range.repo), [])

      # An empty introduced in 0.7 now needs to be represented as '0' in 0.8.
      introduced = AffectedEvent(
          type='introduced', value=affected_range.introduced or '0')
      if introduced not in events:
        events.append(introduced)

      if affected_range.fixed:
        fixed = AffectedEvent(type='fixed', value=affected_range.fixed)
        if fixed not in events:
          events.append(fixed)

    for (range_type, repo_url), events in events_by_type.items():
      affected_range = AffectedRange2(type=range_type, events=events)

      if range_type == 'GIT' and repo_url:
        affected_range.repo_url = repo_url

      affected_package.ranges.append(affected_range)

  def _get_pre_0_8_affects(self):
    """Get pre 0.8 schema affects field."""
    affected_package = self.affected_packages[0]
    affects = vulnerability_pb2.Affects(versions=affected_package.versions)
    for affected_range in affected_package.ranges:
      # Convert flattened events to range pairs (pre-0.8 schema).
      # TODO(ochang): Remove this once all consumers are migrated.
      # pylint: disable=cell-var-from-loop
      new_range = lambda: vulnerability_pb2.AffectedRange(
          type=vulnerability_pb2.AffectedRange.Type.Value(affected_range.type),
          repo=affected_range.repo_url)
      cur_range = new_range()

      # Sort the flattened events, then find corresponding [introduced,
      # fixed) pairs.
      for event in sorted_events(affected_package.package.ecosystem,
                                 affected_range.type, affected_range.events):
        if event.type == 'introduced':
          if cur_range.introduced and affected_range.type == 'GIT':
            # If this is GIT, then we need to store all "introduced", even if
            # they overlap.
            affects.ranges.append(cur_range)
            cur_range = new_range()

          if not cur_range.introduced:
            # If not GIT, ignore overlapping introduced versions since they're
            # redundant.
            cur_range.introduced = event.value
            if cur_range.introduced == '0':
              cur_range.introduced = ''

        if event.type == 'fixed':
          # Found a complete pair.
          cur_range.fixed = event.value
          affects.ranges.append(cur_range)
          cur_range = vulnerability_pb2.AffectedRange(
              type=vulnerability_pb2.AffectedRange.Type.Value(
                  affected_range.type),
              repo=affected_range.repo_url)

      if cur_range.introduced:
        affects.ranges.append(cur_range)

    return affects

  def to_vulnerability(self, include_source=False):
    """Convert to Vulnerability proto."""
    package = None
    ecosystem_specific = None
    database_specific = None
    affects = None

    if self.affected_packages:
      # The pre-0.8 schema only supports a single package, so we take the
      # first.
      affected_package = self.affected_packages[0]

      package = vulnerability_pb2.Package(
          name=affected_package.package.name,
          ecosystem=affected_package.package.ecosystem,
          purl=affected_package.package.purl)

      affects = self._get_pre_0_8_affects()
      if affected_package.ecosystem_specific:
        ecosystem_specific = affected_package.ecosystem_specific
      if affected_package.database_specific:
        database_specific = affected_package.database_specific

    details = self.details
    if self.status == bug.BugStatus.INVALID:
      affects = None
      details = 'INVALID'

    if self.last_modified:
      modified = timestamp_pb2.Timestamp()
      modified.FromDatetime(self.last_modified)
    else:
      modified = None

    if self.withdrawn:
      withdrawn = timestamp_pb2.Timestamp()
      withdrawn.FromDatetime(self.withdrawn)
    else:
      withdrawn = None

    published = timestamp_pb2.Timestamp()
    published.FromDatetime(self.timestamp)

    references = []
    if self.reference_url_types:
      for url, url_type in self.reference_url_types.items():
        references.append(
            vulnerability_pb2.Reference(
                url=url, type=vulnerability_pb2.Reference.Type.Value(url_type)))

    result = vulnerability_pb2.Vulnerability(
        id=self.id(),
        published=published,
        modified=modified,
        aliases=self.aliases,
        related=self.related,
        withdrawn=withdrawn,
        summary=self.summary,
        details=details,
        package=package,
        affects=affects,
        references=references)

    if ecosystem_specific:
      result.ecosystem_specific.update(ecosystem_specific)

    if database_specific:
      result.database_specific.update(database_specific)

    if self.source and include_source:
      source_repo = get_source_repository(self.source)
      if not source_repo or not source_repo.link:
        return result

      result.database_specific.update({
          'source': source_repo.link + sources.source_path(source_repo, self),
      })

    return result


class SourceRepositoryType(enum.IntEnum):
  """SourceRepository type."""
  GIT = 0
  BUCKET = 1


class SourceRepository(ndb.Model):
  """Source repository."""
  # The type of the repository.
  type = ndb.IntegerProperty()
  # The name of the source.
  name = ndb.StringProperty()
  # The repo URL for the source.
  repo_url = ndb.StringProperty()
  # The username to use for SSH auth.
  repo_username = ndb.StringProperty()
  # Optional branch for repo.
  repo_branch = ndb.StringProperty()
  # Bucket name.
  bucket = ndb.StringProperty()
  # The directory in the repo where Vulnerability data is stored.
  directory_path = ndb.StringProperty()
  # Last synced hash.
  last_synced_hash = ndb.StringProperty()
  # Last date recurring updates were requested.
  last_update_date = ndb.DateProperty()
  # Patterns of files to exclude (regex).
  ignore_patterns = ndb.StringProperty(repeated=True)
  # Whether this repository is editable.
  editable = ndb.BooleanProperty(default=False)
  # Default extension.
  extension = ndb.StringProperty(default='.yaml')
  # Key path within each file to store the vulnerability.
  key_path = ndb.StringProperty()
  # It true, don't analyze any git ranges.
  ignore_git = ndb.BooleanProperty(default=False)
  # Whether to detect cherypicks or not (slow for large repos).
  detect_cherrypicks = ndb.BooleanProperty(default=True)
  # Whether to populate "versions" from git ranges.
  versions_from_repo = ndb.BooleanProperty(default=True)
  # HTTP link prefix.
  link = ndb.StringProperty()
  # DB prefix, if the database allocates its own.
  db_prefix = ndb.StringProperty()

  def ignore_file(self, file_path):
    """Return whether or not we should be ignoring a file."""
    if not self.ignore_patterns:
      return False

    file_name = os.path.basename(file_path)
    for pattern in self.ignore_patterns:
      if re.match(pattern, file_name):
        return True

    return False

  def _pre_put_hook(self):
    """Pre-put hook for validation."""
    if self.type == SourceRepositoryType.BUCKET and self.editable:
      raise ValueError('BUCKET SourceRepository cannot be editable.')


def get_source_repository(source_name):
  """Get source repository."""
  return SourceRepository.get_by_id(source_name)


def sorted_events(ecosystem, range_type, events):
  """Sort events."""
  if range_type == 'GIT':
    # No need to sort.
    return events

  if range_type == 'SEMVER':
    ecosystem_helper = ecosystems.SemverEcosystem()
  else:
    ecosystem_helper = ecosystems.get(ecosystem)

  # Remove any magic '0' values.
  zero_event = None
  for event in events.copy():
    if event.value == '0':
      zero_event = event
      events.remove(event)

  events = sorted(events, key=lambda e: ecosystem_helper.sort_key(e.value))
  if zero_event:
    events.insert(0, zero_event)

  return events
