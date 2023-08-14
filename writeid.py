sessionid = str(input('sessionid: '))
with open('.env', 'w') as f1:
    f1.write(f'sessionid = "{sessionid}"')
print('written successfully!')