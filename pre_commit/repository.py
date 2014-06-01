from asottile.cached_property import cached_property
from asottile.ordereddict import OrderedDict

from pre_commit.languages.all import languages
from pre_commit.manifest import Manifest
from pre_commit.prefixed_command_runner import PrefixedCommandRunner


class Repository(object):
    def __init__(self, repo_config, repo_path_getter):
        self.repo_config = repo_config
        self.repo_path_getter = repo_path_getter
        self.__installed = False

    @classmethod
    def create(cls, config, store):
        repo_path_getter = store.get_repo_path_getter(
            config['repo'], config['sha']
        )
        return cls(config, repo_path_getter)

    @cached_property
    def repo_url(self):
        return self.repo_config['repo']

    @cached_property
    def sha(self):
        return self.repo_config['sha']

    @cached_property
    def languages(self):
        return set(hook['language'] for hook in self.hooks.values())

    @cached_property
    def hooks(self):
        # TODO: merging in manifest dicts is a smell imo
        return OrderedDict(
            (hook['id'], dict(hook, **self.manifest.hooks[hook['id']]))
            for hook in self.repo_config['hooks']
        )

    @cached_property
    def manifest(self):
        return Manifest(self.repo_path_getter)

    @cached_property
    def cmd_runner(self):
        return PrefixedCommandRunner(self.repo_path_getter.repo_path)

    def require_installed(self):
        if self.__installed:
            return

        self.install()
        self.__installed = True

    def install(self):
        """Install the hook repository."""
        for language_name in self.languages:
            language = languages[language_name]
            if (
                language.ENVIRONMENT_DIR is None or
                self.cmd_runner.exists(language.ENVIRONMENT_DIR)
            ):
                # The language is already installed
                continue
            language.install_environment(self.cmd_runner)

    def run_hook(self, hook_id, file_args):
        """Run a hook.

        Args:
            hook_id - Id of the hook
            file_args - List of files to run
        """
        self.require_installed()
        hook = self.hooks[hook_id]
        return languages[hook['language']].run_hook(
            self.cmd_runner, hook, file_args,
        )
