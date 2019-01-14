# dropbox-event-feed-to-mail
A python3 script to send dropbox event list to mail

*Setup*

To use it you must create a Dropbox app, see https://www.dropbox.com/developers/apps/create

After that, edit the .py file and set your API key and the email address that will receive the event feed.

Your system must have "curl" and "sendmail" commands available.

*Usage*

First time you execute the scipt it will initilize the cursor to current dropbox status.

After that, each time you execue the script it will fetch changes from previous running, sort them and send them to email address specified in header.

You can put the script in your crontab, executing it once a day or every X hours.
