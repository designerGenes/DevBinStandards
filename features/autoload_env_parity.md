## Autoload Environment Parity

1. let's update our autoload_environment script so that subdirectory-contained .env files can reference other directories' .env values.  Our situation is this: the value of TAVILY_API_KEY is set in the $HOME/dev/.env file, but we want to be able to reference that value from within a project-specific .env file located at $HOME/dev/tavily-search/.env.  If we create a .eng file in the tavily-search directory with the following content:

```
TAVILY_API_KEY=${$HOME/dev/.env:TAVILY_API_KEY}
```

then when we run our autoload_environment script from within the tavily-search directory, it should correctly resolve TAVILY_API_KEY to the value defined in $HOME/dev/.env.

2. We also want to be able to simply defer to the parent directory's .env file without explicitly specifying the path.  For example, if we have a .env file in $HOME/dev/bin/python/tavily-search/ with the following content:

```
TAVILY_API_KEY=DEFER_PARENT
```

then when we run our autoload_environment script from within the tavily-search directory, it should look for a .env file in the parent directory ($HOME/dev/bin/python/) and load TAVILY_API_KEY from there.  If there are multiple levels of parent directories, it should continue searching upwards until it finds a .env file or reaches the root directory.  

If there are multiple instances of the key found across multiple .env files in the same directory hierarchy, the value from the closest .env file to the current working directory should take precedence.

3. Finally, we want to be able to provide the ability to fetch values from the CLI application "skate".  You can run "skate --help" to understand its capabilities.  For example, if we have a .env file in $HOME/dev/tavily-search/ with the following content:

```
TAVILY_API_KEY=${skate get foo@internal}
```

then when we run our autoload_environment script from within the tavily-search directory, it should execute the command "skate get foo@internal" and set TAVILY_API_KEY to the output of that command.