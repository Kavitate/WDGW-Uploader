<h1 align="center">:pager::satellite: Watch Dogs Go Wars Discord Bot Uploader :satellite::pager:</h1>

<p align="center">
  <img src="https://i.imgur.com/XpcN6uA.png">
</p>

## Screenshots
<p float="left">
  <img align="center" src="https://i.imgur.com/ynj72Bq.png"/><br/><br/>
  <img align="center" src="https://i.imgur.com/g1gIzJb.png"/>
</p>

<p float="left">
  <img align="center" src="https://i.imgur.com/2LCQ1Cs.png"/><br/><br/>
  <img align="center" src="https://i.imgur.com/z3tABuV.png"/>
</p>

<p float="left">
  <img align="center" src="https://i.imgur.com/Ek8qxLU.png" width="1000" height="300"/>
</p>

## Purpose
A Discord bot that pulls your latest [WiGLE](https://wigle.net/) upload and pushes it to [Watch Dogs Go Wars](https://wdgwars.pl/) using APIs from both sites as shown above.

I primarily wardrive using the [WiGLE WiFi Wardriving](https://play.google.com/store/apps/details?id=net.wigle.wigleandroid&hl=en_US) app.<br/><br/>
Since the release of Watch Dogs Go Wars the only way to upload runs conducted on the WiGLE app is to manually download them and upload them on the WDGW website.<br/><br/>
Utilizing this bot eliminates the need for the user to manually download and upload.<br/><br/>
With the use of a simple `/sync` command, the bot will download the latest upload from WiGLE and upload it to your account on WDGW.

## Variables
Prior to using the bot the following variables must be changed in the `config.json` file:
- Remove the `XXXX` text in `discord_token` and replace it with your Discord Bot Token.
  - If you do not know how to create a Discord bot, instructions on how to do so can be found [here](https://discordpy.readthedocs.io/en/stable/discord.html)
- Remove the `XXXX` text in `wigle_api_token` and replace it with your WiGLE API Key.
  - Your API key can be found [here](https://api.wigle.net/), select your account page in the lower right, then select "Show My Token".
  - The token you are looking for will be listed as the "Encoded for use".
- Remove the `XXXX` text in `wdgwars_api_key` and replace it with your Watch Dogs Go Wars API Key.
  - Your API key can be found [here](https://wdgwars.pl/profile/), scroll down to "API Keys", and generate a new key with the name "Discord Bot" for example.

## Commands
Once the above variables have been updated, run the bot using the following commands:
- `/sync` to pull the latest WiGLE upload and push it to WDGW.
- `/help` to display helpful information for the WDGW Uploader.
