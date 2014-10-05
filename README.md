donationbox
===========

feed the coin acceptor with money, smile while an image is taken and wait for your printout

svipi.noip.me:5000

to start the script, edit roots crontab by typing:

sudo crontab -e

add this line to your crontab:

@reboot sh /usr/local/bin/donationbox/init-donationbox.sh >/home/pi/logs/cronlog 2>&1
