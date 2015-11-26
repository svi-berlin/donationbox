donationbox
===========

feed the coin acceptor with money, smile while an image is taken and wait for your printout

inspired by: http://blog.notdot.net/2012/09/Penny-for-your-thoughts
also check: https://jalibu.wordpress.com/2014/12/24/my-raspberry-pi-advice-machine/

svipi.noip.me:5000

to start the script, edit roots crontab by typing:

sudo crontab -e

add this line to your crontab:

@reboot sh /usr/local/bin/donationbox/init-donationbox.sh >/home/pi/logs/cronlog 2>&1
