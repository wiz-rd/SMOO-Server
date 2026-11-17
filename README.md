# SMOO Server

This is a simple implementation of the official [SMOO Server](https://github.com/Sanae6/SmoOnlineServer). This does *not* support UDP or Hide & Seek but does support Moons (internally called Shines) syncing and player sync.

## Running the server

To run this server, use [UV](https://docs.astral.sh/uv/) as it will automatically install all of the packages you need. Then, do the following:

- Clone this repository or use `Code > Download as zip`
- `cd` into this repository's folder in a terminal
- Run `uv run main.py`

UV should download all the packages you need and the server should start up automatically. It listens on the default port of **1027**.

### Config

***NOTE:*** for testing reasons, users with the name "tom" or "ben" are banned. To change this and other configuration options, open `config.toml` in a text editor and change those values.
