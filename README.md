[![Build Status](https://travis-ci.org/reticulatingspline/Soccer.svg?branch=master)](https://travis-ci.org/reticulatingspline/Soccer)

# Limnoria plugin for Soccer

## Introduction

I started this as just a way to display some scores / fixtures from the major leagues and
got a ton of requests to expand it. Also displays the table, stat (goals/assist) leaders,
FIFA Rankings and formation information for a match if available.

## Install

You will need a working Limnoria bot on Python 2.7 for this to work.

Go into your Limnoria plugin dir, usually ~/supybot/plugins and run:

```
git clone https://github.com/reticulatingspline/Soccer
```

To install additional requirements, run:

```
pip install -r requirements.txt 
```

Next, load the plugin:

```
/msg bot load Soccer
```

That's it. You're done.

## Example Usage

```
<spline> @fifarankings
<myybot> FIFA Rankings (2014-9) :: 1. Germany - 1765.00(-) | 2. Argentina - 1631.00(-) | 3.
<spline> @soccer epl
<myybot> FT - Manchester United 2-1 Everton | FT - Chelsea 2-0 Arsenal | FT - Tottenham Hotspur 1-0 Southampton | FT - West Ham United 2-0 Queens Park Rangers
<spline> @soccertable epl
<myybot> epl :: 1. Chelsea (19) | 2. Manchester City (14) | 3. Southampton (13) | 4. Manchester United (11) 
<spline> @soccerstats epl goals
<myybot> Top 5 scorers in epl :: Diego Costa (Chelsea) 9 | Leonardo Ulloa (Leicester City) 5 
```

## About

All of my plugins are free and open source. When I first started out, one of the main reasons I was
able to learn was due to other code out there. If you find a bug or would like an improvement, feel
free to give me a message on IRC or fork and submit a pull request. Many hours do go into each plugin,
so, if you're feeling generous, I do accept donations via Amazon or browse my [wish list](http://amzn.com/w/380JKXY7P5IKE).

I'm always looking for work, so if you are in need of a custom feature, plugin or something bigger, contact me via GitHub or IRC.