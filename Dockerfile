FROM ubuntu:latest
LABEL authors="yvansiaka"

# Set timezone here or apache installation will stop there
ENV TZ=Africa/Douala
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

RUN apt-get update --fix-missing
RUN apt-get install -y pkg-config

RUN apt-get update --fix-missing
RUN apt-get install -y libpq-dev build-essential

# Python installs
RUN apt-get install -y python
RUN apt-get install -y python3-pip
RUN apt-get install -y libapache2-mod-wsgi-py3

# Install mysqlclient dev lib
RUN apt-get install -y libmysqlclient-dev


RUN pip3 install arabic-reshaper==3.0.0
RUN pip3 install asgiref==3.8.1
RUN pip3 install asn1crypto==1.5.1
RUN pip3 install blinker==1.8.2
RUN pip3 install bson==0.5.10
RUN pip3 install certifi==2024.2.2
RUN pip3 install cffi==1.16.0
RUN pip3 install chardet==5.2.0
RUN pip3 install charset-normalizer==3.3.2
RUN pip3 install click==8.1.7
RUN pip3 install cryptography==42.0.5
RUN pip3 install cssselect2==0.7.0
RUN pip3 install defusedxml==0.7.1
RUN pip3 install diff-match-patch==20230430
RUN pip3 install Django==5.0.4
RUN pip3 install django-cors-headers==4.3.1
RUN pip3 install django-import-export==3.3.8
RUN pip3 install django-rest-passwordreset==1.4.1
RUN pip3 install django-user-agents==0.4.0
RUN pip3 install django-utils-six==2.0
RUN pip3 install djangorestframework==3.15.1
RUN pip3 install docopt==0.6.2
RUN pip3 install et-xmlfile==1.1.0
RUN pip3 install Flask==3.0.3
RUN pip3 install Flask-MySQLdb==2.0.0
RUN pip3 install html5lib==1.1
RUN pip3 install idna==3.7
RUN pip3 install itsdangerous==2.2.0
RUN pip3 install Jinja2==3.1.4
RUN pip3 install lxml==5.2.1
RUN pip3 install MarkupPy==1.14
RUN pip3 install MarkupSafe==2.1.5
RUN pip3 install mysql-client==0.0.1
RUN pip3 install mysqlclient==2.2.4
RUN pip3 install num2words==0.5.13
RUN pip3 install odfpy==1.4.1
RUN pip3 install openpyxl==3.1.2
RUN pip3 install oscrypto==1.3.0
RUN pip3 install pillow==10.2.0
RUN pip3 install pycparser==2.21
RUN pip3 install pyHanko==0.21.0
RUN pip3 install pyhanko-certvalidator==0.26.3
RUN pip3 install pypdf==4.0.2
RUN pip3 install pypng==0.20220715.0
RUN pip3 install python-bidi==0.4.2
RUN pip3 install python-dateutil==2.8.2
RUN pip3 install python-slugify==8.0.1
RUN pip3 install pytz==2023.3.post1
RUN pip3 install PyYAML==6.0.1
RUN pip3 install qrcode==7.4.2
RUN pip3 install reportlab==4.0.9
RUN pip3 install requests==2.31.0
RUN pip3 install six==1.16.0
RUN pip3 install sqlparse==0.4.4
RUN pip3 install svglib==1.5.1
RUN pip3 install tablib==3.5.0
RUN pip3 install text-unidecode==1.3
RUN pip3 install tinycss2==1.2.1
RUN pip3 install typing_extensions==4.9.0
RUN pip3 install tzdata==2023.4
RUN pip3 install tzlocal==5.2
RUN pip3 install ua-parser==0.18.0
RUN pip3 install uritools==4.0.2
RUN pip3 install urllib3==2.2.0
RUN pip3 install user-agents==2.2.0
RUN pip3 install webencodings==0.5.1
RUN pip3 install Werkzeug==3.0.3
RUN pip3 install xhtml2pdf==0.2.15
RUN pip3 install xlrd==2.0.1
RUN pip3 install xlwt==1.3.0

# Deactivate the default .conf file
RUN unlink /etc/apache2/sites-enabled/000-default.conf


COPY . .

RUN chown -R root:www-data /easypro237/

# Enable the virtual host in apache
RUN ln -sf /easypro237/apache_docker.conf /etc/apache2/sites-enabled/easypro237.conf

# Enable headers module
RUN a2enmod headers

WORKDIR /easypro237

EXPOSE 80

# Run apache2 as foreground process
CMD ["/usr/sbin/apache2ctl", "-DFOREGROUND"]

#ENTRYPOINT ["top", "-b"]