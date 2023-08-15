import subprocess, sys, os
def main():
    subprocess.run('pip install -r requirements.txt'.split())
    if not os.path.exists('env.py'):
        try:
            import pygame

            pygame.mixer.init()

            sound_file = "the.wav"
            sound = pygame.mixer.Sound(sound_file)

            sound.play()
            subprocess.run('python writeid.py'.split())
        except Exception as e:
            print(e)
            input()
    if sys.platform.startswith('win'):
        subprocess.run('pip install cx_Freeze'.split())

        from cx_Freeze import setup, Executable

        build_options = {'packages': ['requests', 'json', 're', 
                                      'os', 'tqdm', 'datetime', 
                                      'argparse', 'dotenv', 'logging'], 'excludes': [], 'optimize': 2}

        base = 'console'

        executables = [
            Executable('insta.py', base=base)
        ]

        setup(name='instadownloader',
            version = '1.0',
            description = 'downloads instagram posts and reels',
            options = {'build_exe': build_options},
            executables = executables)

        pathtoexe = "insta.exe"
        for root, dirs, files in os.walk('.'):
            if pathtoexe in files:
                filepath = os.path.abspath(root)
                break
        import winreg

        def add_to_path(directory, user=False):
            if user:
                key = winreg.HKEY_CURRENT_USER
                subkey = 'Environment'
            else:
                key = winreg.HKEY_LOCAL_MACHINE
                subkey = r'SYSTEM\CurrentControlSet\Control\Session Manager\Environment'

            with winreg.OpenKey(key, subkey, 0, winreg.KEY_ALL_ACCESS) as regkey:
                path_value, _ = winreg.QueryValueEx(regkey, 'Path')
                print(path_value)
                if directory not in path_value:
                    path_value += ';' + directory
                    winreg.SetValueEx(regkey, 'Path', 0, winreg.REG_EXPAND_SZ, path_value)
                else:
                    print(f'{directory} is already in path:\n{path_value}')

        directory_path = filepath

        add_to_path(directory_path)
    
    elif sys.platform.startswith('linux'):
        #cant build to exe on linux
        pathtopy = "insta.py"
        for root, dirs, files in os.walk('.'):
            if pathtopy in files:
                filepath = os.path.abspath(root)
                break
        with open(os.path.join(filepath, pathtopy), 'r') as f1:
            script = f1.read()
        with open(os.path.join(filepath, pathtopy), 'w') as f1:
            f1.write('#!/usr/bin/env python\n' + script)
        homedirectory = os.path.expanduser('~')
        profilefile = os.path.join(homedirectory, '.bashrc')
        print(os.path.abspath(profilefile))
        with open(profilefile, 'a') as f1:
            f1.write(f'\nexport PATH="$PATH:{filepath}"\n')
        print(f'usage: {filepath + "/insta.py"} to execute')
        with open('usagecommand.txt', 'w') as f1:
            f1.write(f'{filepath + "/insta.py"}')
        subprocess.run(f'chmod +x {filepath + "/insta.py"}'.split())
        
if __name__ == '__main__':
    if sys.platform.startswith('win'):
        subprocess.run('pip install pyuac'.split())
        subprocess.run('pip install pypiwin32'.split())
        import pyuac
        if not pyuac.isUserAdmin():
            pyuac.runAsAdmin()
        else:
            main()
    elif sys.platform.startswith('linux'):
        if os.getuid() != 0:
            print('run as admin! (sudo)')
        else:
            main()