## Name
Builder365

## Description
Let people know what your project can do specifically. Provide context and add a link to any reference visitors might be unfamiliar with. A list of Features or a Background subsection can also be added here. If there are alternatives to your project, this is a good place to list differentiating factors.

## Installation Guide

We recommend ubuntu 20.04. These instructions are verified for ubuntu 20.04.

#### To install system requirments

```
sudo apt update && sudo apt upgrade -y

sudo apt install python-is-python3 xvfb libfontconfig wkhtmltopdf python3-dev python3-pip build-essential libssl-dev libffi-dev python3-venv redis-server redis-tools virtualenv -y
```

#### Install dependencies

##### Optional (based on personal choice)

```
sudo apt update && sudo apt upgrade -y && sudo apt install zsh python3-virtualenv

sh -c "$(wget -O- https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)"

pip install virtualenvwrapper

echo "source /home/ubuntu/.local/bin/virtualenvwrapper.sh" >> ~/.zshrc
```

If you want to install postgres, follow https://www.postgresql.org/download/
#### To modify postgresql root password

```
sudo -u postgres psql
ALTER USER postgres WITH PASSWORD 'root';
```

#### Create and activate a virtual environment.
if you installed and configured virtualenv wrapper then use the following
``` 
mkvirtualenv <env_name>
workon <env_name>
```
or else
```
virtualenv venv
source venv/bin/activate
```
Install the project's dependency after activating env

```
pip install -r requirements.txt
```

### Env variables

* Then refer to `env.example` for environment variables and keep those in the `.env` file in the current folder as your project is in.


### Docker / docker-compose
in order to use docker, please run the next commands after cloning repo:
```
docker build -t djcrm:1 -f docker/Dockerfile .
docker-compose -f docker/docker-compose.yml up
```

**Note**: you must have docker/docker-compose installed on your host. 
### next steps


```
python manage.py makemigrations
python manage.py migrate

python manage.py loaddata lead_list
python manage.py loaddata catalog
python manage.py createcachetable
python manage.py runserver
```
- Then open http://localhost:8000/api/ in your borwser to explore API.

- After running API, Go to Frontend UI [React Builder365 FE](https://github.com/fds-co-ltd/Builder365-FE "FE") project to configure Fronted UI to interact with API.


## Start celery worker in another terminal window

celery -A lcm worker --pool=solo --loglevel=info
