#!/usr/bin/python3
# require python3
# -*- coding: utf-8 -*-

# To generate a token look at: https://www.dropbox.com/developers/documentation/http/documentation
DROPBOX_APP_TOKEN = '...'

# Email changes to this address
EMAIL_TO = '...'

# Save temporary data (cursor) to this file
CURSOR_FILE = 'dropbox-event-feed-to-mail.data'

# Commands used
COMMAND_GET_LATEST_CURSOR = 'curl -s -X POST https://api.dropboxapi.com/2/files/list_folder/get_latest_cursor --header "Authorization: Bearer {TOKEN}" --header "Content-Type: application/json" --data "{\\"path\\": \\"\\",\\"recursive\\": true,\\"include_deleted\\": true}"'
COMMAND_LIST_FOLDER_CONTINUE = 'curl -s -X POST https://api.dropboxapi.com/2/files/list_folder/continue --header "Authorization: Bearer {TOKEN}" --header "Content-Type: application/json" --data "{\\"cursor\\": \\"{CURSOR}\\"}"'
#COMMAND_SEND_MAIL = 'echo -ne "Subject: {SUBJECY}\nContent-Type: text/html\n\n{BODY}" | sendmail {EMAIL_TO}'
COMMAND_SEND_MAIL = 'sendmail {EMAIL_TO}'

#------------------------------------------------------------------------------

import logging
import subprocess
import os
import json
import quopri
import time

currdir = os.path.realpath(os.path.dirname(__file__))

def send_mail(subject, body):
  try:
    input = "Subject: " + subject + "\nContent-Type: text/html; charset=\"UTF-8\"\nContent-Transfer-Encoding: quoted-printable\n\n" + body
    output = subprocess.check_output(COMMAND_SEND_MAIL.replace('{EMAIL_TO}', EMAIL_TO), input = quopri.encodestring(input.encode("utf-8")), shell=True).decode("utf-8")
    #output = subprocess.check_output(COMMAND_SEND_MAIL.replace('{SUBJECY}', subject.replace('"', '\\"')).replace('{BODY}', body.replace('"', '\\"')).replace('{EMAIL_TO}', EMAIL_TO), shell=True).decode("utf-8")
    return True
  except:
    logging.exception("failed sending mail")
    return False

def cursor_save(cursor):
    try:
      if os.path.isfile(currdir + '/' + CURSOR_FILE + '.new'):
        os.remove(currdir + '/' + CURSOR_FILE + '.new')
      with open(currdir + '/' + CURSOR_FILE + '.new', 'w') as f:
        f.write(cursor)
      if os.path.isfile(currdir + '/' + CURSOR_FILE + '.new'):
        if os.path.isfile(currdir + '/' + CURSOR_FILE):
          if os.path.isfile(currdir + '/' + CURSOR_FILE + '.bak'):
            os.remove(currdir + '/' + CURSOR_FILE + '.bak')
          os.rename(currdir + '/' + CURSOR_FILE, currdir + '/' + CURSOR_FILE + '.bak')
        os.rename(currdir + '/' + CURSOR_FILE + '.new', currdir + '/' + CURSOR_FILE)
    except:
      logging.exception("failed saving cursor file")
  

# @see https://www.dropbox.com/developers/documentation/http/documentation#files-list_folder-get_latest_cursor
def cursor_fetch():
  cursor = None
  if os.path.isfile(currdir + '/' + CURSOR_FILE):
    with open(currdir + '/' + CURSOR_FILE, 'r') as f:
      cursor = f.read().strip()
  else:
    try:
      cmd = COMMAND_GET_LATEST_CURSOR.replace('{TOKEN}', DROPBOX_APP_TOKEN)
      print("Fetching " + cmd + ' ...')
      output = subprocess.check_output(cmd, shell=True).decode("utf-8")
      try:
        output = json.loads(output)
        if 'cursor' in output:
          cursor = output['cursor']
          cursor_save(cursor)
          cursor = None
          send_mail('DROPBOX EVENTS: initialized', '<html><body><h1>Initialized cursor, no data available right now.<h1><p>This should happen only the first time you run the app.</p></body></html>')
        else:
          logging.error("failed decoding last cursor json from Dropbox: " + str(output))
      except:
        logging.exception("failed decoding last cursor data from Dropbox: " + str(output))
    except:
      logging.exception("failed getting last cursor from Dropbox")
  
  return cursor

# @see https://www.dropbox.com/developers/documentation/http/documentation#files-list_folder-continue
def updates_fetch(cursor):
  try:
    cmd = COMMAND_LIST_FOLDER_CONTINUE.replace('{TOKEN}', DROPBOX_APP_TOKEN).replace('{CURSOR}', cursor)
    print("Fetching " + cmd + ' ...')
    output = subprocess.check_output(cmd, shell=True).decode("utf-8")
    try:
      output = json.loads(output)
      if 'cursor' in output and 'entries' in output:
        return output
      elif 'error' in output and 'retry_after' in output['error']:
        logging.debug('sleep requested... ' + str(output))
        time.sleep(output['error']['retry_after'])
        return {'entries': [], 'cursor': cursor, 'has_more': True};
      else:
        logging.error("failed decoding updates json from Dropbox: " + str(output))
    except:
      logging.exception("failed decoding updates data from Dropbox: " + str(output))
  except:
    logging.exception("failed getting updates data from Dropbox")

  return None

def main():
  cursor = cursor_fetch()
  if cursor:
    entries = {}
    cont = True
    while cont:
      data = updates_fetch(cursor)
      cont = False
      if data and 'entries' in data:
        print("Got data for " + str(len(data['entries'])) + " entries ...")
        for e in data['entries']:
          entries[e['path_lower']] = e
          entries[e['path_lower']]['count'] = 0
        if data['has_more'] and data['entries']:
          cursor = data['cursor']
          time.sleep(5)
          cont = True

    if data and 'cursor' in data:
      prev = False
      for path in sorted(entries):
        #if prev and (entries[path]['.tag'] == 'file' or entries[path]['.tag'] == 'folder') and path.startswith(prev):
        if prev and entries[path]['.tag'] == 'file' and path.startswith(prev):
          entries[prev]['count'] = entries[prev]['count'] + 1
          del entries[path]
        elif entries[path]['.tag'] == 'folder':
          prev = path
      
      html = '<html><body>'
      html += '<h1>Dropbox recent events</h1>\n'
      html += '<ul>\n'
      for path in sorted(entries):
        e = entries[path]
        html += '<li>[' + e['.tag'] + '] <a href="https://www.dropbox.com/home' + e['path_lower'] + '" target="_blank">' + e['path_display'] + (' (+ ' + str(e['count']) + ' items)' if e['count'] else '') + '</a></li>\n'
      html += '</ul>\n'
      html += '<p>Full event feed: <a href="https://www.dropbox.com/events" target="_blank">https://www.dropbox.com/events</a></p>\n'
      html += '<h3>Raw data (last)</h3>\n'
      html += '<code>' + str(data) + '</code>\n'
      html += '<h3>Old cursor</h3><code>' + cursor + '</code><h3>New cursor</h3><code>' + data['cursor'] + '</code>\n'
      send_mail('Dropbox recent events', html)
        
      cursor_save(data['cursor'])

if __name__ == '__main__':
  main()
