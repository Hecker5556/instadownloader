sessionid = str(input('sessionid: '))
csrftoken = str(input("csrftoken: "))
with open('env.py', 'w') as f1:
    f1.write(f'sessionid = "{sessionid}"\ncsrftoken = "{csrftoken}')
print('written successfully!')