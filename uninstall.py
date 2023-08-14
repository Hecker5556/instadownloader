import sys, os, shutil, subprocess
if sys.platform.startswith('win'):
    import pyuac 

    if not pyuac.isUserAdmin():
        pyuac.runAsAdmin()
    filepath = None
    pathtoexe = "insta.exe"
    for root, dirs, files in os.walk('.'):
        if pathtoexe in files:
            filepath = os.path.abspath(root)
            break
    if not filepath:
        print('couldnt find insta.exe')
        sys.exit()
    import winreg
    def remove_from_path(directory, user=False):
        if user:
            key = winreg.HKEY_CURRENT_USER
            subkey = 'Environment'
        else:
            key = winreg.HKEY_LOCAL_MACHINE
            subkey = r'SYSTEM\CurrentControlSet\Control\Session Manager\Environment'

        with winreg.OpenKey(key, subkey, 0, winreg.KEY_ALL_ACCESS) as regkey:
            path_value, _ = winreg.QueryValueEx(regkey, 'Path')
            print(path_value)
            if directory in path_value:
                path_value = path_value.replace(';'+directory, '')
                winreg.SetValueEx(regkey, 'Path', 0, winreg.REG_EXPAND_SZ, path_value)
                print('removed from PATH')
            else:
                print(f'{directory} was not in the path!')

    directory_path = filepath

    remove_from_path(directory_path)
    if os.path.exists('build'):
        shutil.rmtree('build')
        print('removed built (exe) files')
    a = str(input('do you wish to also delete this directory?: [y/n]')).lower()
    if a not in ['y', 'n'] or a == 'n':
        print('ok not deleting')
        sys.exit()
    else:
        print('goodbye world')
        subprocess.run(f'rmdir /s {os.path.dirname(os.path.abspath(__file__))}'.split())
elif sys.platform.startswith('linux'):
    if os.getuid() != 0:
        print('execute with sudo!')
    else:
        pathtopy = "insta.py"
        for root, dirs, files in os.walk('.'):
            if pathtopy in files:
                filepath = os.path.abspath(root)
                break
        homedirectory = os.path.expanduser('~')
        profilefile = os.path.join(homedirectory, '.bashrc')
        with open(profilefile, 'r') as f1:
            bashrc = f1.read()
        with open(profilefile, 'w') as f1:
            f1.write(bashrc.replace(f'export PATH="$PATH:{filepath}"', ''))
        print('removed from PATH')
        a = str(input('do you also want to remove this directory?: [y/n]')).lower()
        if a not in ['y', 'n'] or a == 'n':
            print('ok not deleting goodbye')
        else:
            print('goodbye world')
            subprocess.run(f'rm -rf {os.path.dirname(os.path.abspath(__file__))}'.split())