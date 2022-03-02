# Contributing to the Ansible Conjur Collection

For general contribution and community guidelines, please see the [community repo](https://github.com/cyberark/community).

## Releasing

From a clean instance of main, perform the following actions to release a new version
of this plugin:

- Update the version number in [`galaxy.yml`](galaxy.yml) and [`CHANGELOG.md`](CHANGELOG.md)
    - Verify that all changes for this version in `CHANGELOG.md` are clear and accurate,
      and are followed by a link to their respective issue
    - Create a PR with these changes

- Create an annotated tag with the new version, formatted as `v##.##.##`
    - This will kick off an automated script which publish the release to
      [Ansible Galaxy](https://galaxy.ansible.com/cyberark/conjur)

- Create the release on GitHub for that tag
    - Build the release package with `./ci/build_release`
    - Attach package to Github Release

## Set up a development environment

**Note**: If you are going to debug Conjur using [RubyMine IDE](https://www.jetbrains.com/ruby/) or [Visual Studio Code IDE](https://code.visualstudio.com),
see [RubyMine IDE Debugging](#rubymine-ide-debugging) or [Visual Studio Code IDE debugging](#visual-studio-code-ide-debugging) respectively before setting up the development environment.

The `dev` directory contains a `docker-compose` file which creates a development
environment with a database container (`pg`, short for *postgres*), and a
`conjur` server container with source code mounted into the directory
`/cyberark/dev/`.

To use it:

1. Install dependencies (as above)

1. Start the container (and optional extensions):

  ```sh-session
   $ cd dev
   $ ./start.sh
   ...
   root@f75015718049:/cyberark/dev/#
  ```

   Once the `start` script finishes, you're in a Bash shell inside the Conjur
   server container.  To

   After starting Conjur, your instance will be configured with the following:
   * Account: `cucumber`
   * User: `admin`
   * Password: Run `cat conjur.identity` inside the container shell to display the current logged-in identity (which is also the password)

1. Debug the server

  ```sh-session
   root@f39015718062:docker-compose exec <container-service-name> bash
   <various startup messages, then finally:>
   Use exit to stop
   ```

## Testing

    To run a specific set of tests:

    ```sh-session
     $ cd tests
     $ ./test.sh -d <role or plugin name>
     ```
    To run all tests:

     ```sh-session
     $ cd tests
     $ ./test.sh -a
     ```
