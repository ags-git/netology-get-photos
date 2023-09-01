import os
import requests
import json
from datetime import datetime
import webbrowser


class Logger:
    log_filename = 'backup.log'

    def log_message(self, message):
        with open(self.log_filename, 'a') as f:
            f.write(message + '\n')


class VK_API_Client(Logger):
    API_BASE_URL = 'https://api.vk.com/method/'
    REGISTER_URL = 'https://oauth.vk.com/authorize?client_id=51732033&scope=65536&response_type=token'

    def __init__(self, user_id, token='7ab58b227ab58b227ab58b22b879a0d56377ab57ab58b221e55f269e339c772c87231f1'):
        self.token = token
        self.photos = ''
        self.loaded_files = []
        self.log_message(f'STARTING AT {datetime.now()}')
        self.register(user_id)
        self.user_id = user_id

    def get_common_params(self):
        return {
            'access_token': self.token,
            'v': '5.131'
        }

    def register(self, user_id):
        with open('users', 'r') as f:
            users = [line.strip() for line in f]

        self.registered = user_id in users
        if not self.registered:
            webbrowser.open(self.REGISTER_URL)
        return user_id

    def save_user(self, user_id):
        if not self.registered:
            with open('users', 'a') as f:
                f.write(user_id)

    def get_photos(self, album_id):
        url = f'{self.API_BASE_URL}/photos.get'
        params = self.get_common_params()
        params.update({'owner_id': self.user_id, 'album_id': album_id, 'extended': 1, 'photo_sizes': 0})

        self.log_message(f'GET to {url}')
        response = requests.get(url, params=params)
        self.log_message(f'CODE {response.status_code}')

        self.photos = response.json()
        return self.photos

    def load_images(self, count=5):
        self.loaded_files.clear()
        for item in self.photos['response']['items']:
            for size in item['sizes']:
                if size['type'] == 'w':
                    url = size['url']

                    unixtime = int(item['date'])
                    date = datetime.utcfromtimestamp(unixtime).strftime('%Y-%m-%d')
                    filename = f"{item['likes']['count']}_{date}_{item['id']}.jpg"
                    with open(filename, 'wb') as f:
                        self.log_message(f'GET to {url}')
                        response = requests.get(url)
                        self.log_message(f'CODE {response.status_code}')
                        f.write(response.content)

                    self.loaded_files.append({'file_name': filename, 'size': 'w'})

            if len(self.loaded_files) == count:
                break
        return self.loaded_files


class YaD_API_Client(Logger):
    API_BASE_URL = 'https://cloud-api.yandex.net'
    Images_dir = 'VK_Images'
    res_filename = 'backup.json'

    def __init__(self, token):
        self.headers = {'Authorization': f'OAuth {token}'}

    def create_directory(self):
        url = f'{self.API_BASE_URL}/v1/disk/resources'
        params = {'path': self.Images_dir}

        self.log_message(f'GET to {url}')
        response = requests.get(url, params=params, headers=self.headers)
        self.log_message(f'CODE {response.status_code}')

        if response.status_code == 404:
            self.log_message(f'PUT to {url}')
            response = requests.put(url, params=params, headers=self.headers)
            self.log_message(f'CODE {response.status_code}')

        return response.status_code

    def upload_images(self, upload_files):
        uploaded_files = []
        for upload_file in upload_files:
            url = f'{self.API_BASE_URL}/v1/disk/resources/upload'
            params = {'path': f'{self.Images_dir}/{upload_file["file_name"]}'}

            self.log_message(f'GET to {url}')
            response = requests.get(url, params=params, headers=self.headers)
            self.log_message(f'CODE {response.status_code}')

            if response.status_code == 200:
                path_to_upload = response.json().get('href', '')

                with open(upload_file["file_name"], 'rb') as f:
                    self.log_message(f'PUT to {path_to_upload}')
                    response = requests.put(path_to_upload, files={'file': f})
                    self.log_message(f'CODE {response.status_code}')
                    uploaded_files.append(upload_file)
            elif response.status_code == 409:
                print(f'Файл "{upload_file["file_name"]}" уже существует. Пропуск')
            else:
                print(f'Файл "{upload_file["file_name"]}" - ошибка при загрузке, код {response.status_code}. Пропуск')

        with open(self.res_filename, 'w') as f:
            json.dump(uploaded_files, f)
            # json.dump(json.dumps(uploaded_files), f)
        self.log_message(f'COMPLETED AT {datetime.now()}\n')

        return response


def input_user_id():
    while True:
        print('Введите идентификатор пользователя "ВКонтакте":')
        _id = input()
        if _id.isdigit():
            break
        else:
            print('Неверный идентификатор. Нужно ввести число.')
    return _id


def input_yad_token():
    while True:
        print('Введите токен "Я.Диска":')
        _token = input()
        if len(_token) == 58:
            break
        else:
             print('Неверная длина токена. Повторите ввод.')
    return _token


def input_about_profile():
    print('Загрузить фото профиля? (Д/н):')
    _answer = input()
    return _answer == 'Д'


def input_count():
    while True:
        print('Введите количество:')
        _id = input()
        if _id.isdigit():
            break
        else:
            print('Неверное значение. Нужно ввести число.')
    return int(_id)



if __name__ == '__main__':
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    print('Добрый день! Я сохраню Ваши фотографии из сети "ВКонтакте" на "Я.Диск"')
    user_id = input_user_id()
    yad_token = input_yad_token()

    vk_client = VK_API_Client(user_id)
    yad_client = YaD_API_Client(yad_token)

    if input_about_profile():
        photos = vk_client.get_photos('profile')
    else:
        print('Загружаю "Фото на стене"')
        photos = vk_client.get_photos('wall')

    if 'response' in photos:
        vk_client.save_user(vk_client.user_id)

        if yad_client.create_directory() in (200, 201):
            image_count = input_count()
            yad_client.upload_images(vk_client.load_images(image_count))
    else:
        print('Ошибка загрузки данных. Проверьте идентификатор пользователя')
