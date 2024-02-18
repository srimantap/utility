#!/usr/bin/python

'''
 
 * Copyright (C) 2024  Bits For Byte <support@bitsforbyte.com>
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 *
 * Article Link : 
 

 Python script to alert when disk usage is higher than
    expected. We will use cpu usage afterwards.

    Run this as a cronjob on the server.

    1 */1 * * * python <path to script>/machine-alert-monitor.py 


'''

import smtplib
import syslog
import re
import subprocess

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

PARTITION = '/'
THRESOLD = 60
SENDER_EMAIL = '<input sender email>'
SENDER_PASSWORD = '<sender email password>'
ALERT_EMAILS = '<receiver email>'
SMTP_SERVER  = '<smtp server for email>'
SMTP_SERVER_PORT = 587


class MachineAlertMonitorError(Exception):
    pass


class MachineAlertMonitor:
    def __init__(self, email_username, email_password, alert_emails, partition, threshold):
        self.email_username = email_username
        self.email_password = email_password
        self.alert_emails = alert_emails
        self.partition = partition
        self.threshold = threshold

    def format_conversion(self, size):
        ''' Converts to proper format '''
        for x in ['KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f'{size:3.1f} {x}'
            size /= 1024.0
        return f'{size:,}'


    def _get_disk_usage_report(self):
        ''' Returns disk usage and availability '''

        # Get the disk utilization data from the command 'df'.
        try:
            out = subprocess.run(
                ['df'], check=True, capture_output=True, text=True
            )
        except subprocess.SubprocessError as e:
            raise MachineAlertMonitorError(f'Failed to run df: {e}')

        # Parse the output to get the available space and the percentage of disk
        # utilization of the specified disk partition.
        parsed = re.search(
            f'.* (\d+) .* (\d+)%.*{self.partition}\\n', out.stdout
        )
        if parsed is None:
            raise MachineAlertMonitorError('Failed to parse disk usage output')

        return int(parsed.group(1)), int(parsed.group(2))

    def _send_machine_alert(self, available, use):
        ''' Send an email alert to person during machine anomalies'''

        try:
            # creates SMTP session
            smtp_server = smtplib.SMTP(SMTP_SERVER, SMTP_SERVER_PORT)

            # start TLS for security
            smtp_server.starttls()

            # Authentication
            smtp_server.login(self.email_username, self.email_password)

            # Create the message
            message = MIMEMultipart("alternative")
            message["Subject"] = "Attention !!!  Alert : Server Anomalies"
            message["From"] = self.email_username
            message["To"] = self.alert_emails

            # Create the plain-text and HTML version of your message
            text = f"""\
            Dear Admin,

              Server has got machine anomalies.
            
              Used Hard disk space  {use}%.
              Left Hard disk space  {self.format_conversion(available)} only.

            Thanks You,
            MachineAnomaliesBot
            """
            html = f"""\
            <html>
              <body>
                <p style="color:DodgerBlue;">Dear Admin,</p>
                <p style="color:DodgerBlue;">Server has got machine anomalies.</p>

                <h6 style="color:Tomato;"> Used Hard disk space  {use}%.<br>
                Left Hard disk space {self.format_conversion(available)}.</h6>

                <p>  </p>
                <p style="color:DodgerBlue;">Thanks You,<br>
                  MachineAnomaliesBot
                </p>
              </body>
             </html>
             """

            # Turn these into plain/html MIMEText objects
            part1 = MIMEText(text, "plain")
            part2 = MIMEText(html, "html")

            # Add HTML/plain-text parts to MIMEMultipart message
            # The email client will try to render the last part first
            message.attach(part1)
            message.attach(part2)

            smtp_server.sendmail(self.email_username, self.alert_emails, message.as_string())
        except (
            smtplib.SMTPException,
            smtplib.SMTPAuthenticationError,
        ) as e:
            raise MachineAlertMonitorError(f'Failed to send email : {e}')


    def monitor(self):
        ''' Send an email during machine anomalies'''
        available, use = self._get_disk_usage_report()
        print("available : %d, use : %d" % (available, use))
        if use >= self.threshold:
            print("Send a alert to recipient")
            self._send_machine_alert(available, use)



if __name__ == '__main__':
    try:
        MachineAlertMonitor(SENDER_EMAIL, SENDER_PASSWORD, ALERT_EMAILS, PARTITION, THRESOLD).monitor()
    except MachineAlertMonitorError as e:
        syslog.syslog(syslog.LOG_ALERT, str(e))
