import os
import re
import subprocess
import datetime
import time
from pathlib import Path
import psutil

# Define colors
GREEN = '\033[1;32m'
RED = '\033[1;31m'
NC = '\033[0m'  # No Color
GREY = '\033[90m'

OUTPUT_CONTENT = ''

# Function to check for the process
def old_check_process(process_name):
    result = subprocess.run(['pgrep', '-fl', process_name], stdout=subprocess.PIPE).stdout.decode().strip()
    return result.split('\n')

def check_process(process_name):
    result = subprocess.run(['pgrep', '-fl', process_name], stdout=subprocess.PIPE).stdout.decode().strip()
    return result.split('\n') if result else []

# Function to get the last timestamp from the log
def old_get_last_timestamp(log_file):
    last_timestamp = None
    try:
        with open(log_file, 'r') as file:
            lines = file.readlines()
        for line in reversed(lines):
            match = re.search(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}', line)
            if match:
                last_timestamp = match.group(0)
                break
    except Exception as e:
        output(f"{RED}Error reading log file: {e}{NC}")
    return last_timestamp

# Function to get the last ERROR timestamp from the log
def get_last_error_timestamp(log_file):
    last_error_timestamp = None
    try:
        with open(log_file, 'r') as file:
            lines = file.readlines()
        for line in reversed(lines):
            if line.startswith("ERROR"):
                match = re.search(r'ERROR (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', line)
                if match:
                    last_error_timestamp = match.group(1)
                    break
    except Exception as e:
        print(f"Error reading log file: {e}")
    return last_error_timestamp

# Function to calculate difference in days
def calculate_days_difference(timestamp1, timestamp2):
    time_format = "%Y-%m-%d %H:%M:%S"
    t1 = datetime.datetime.strptime(timestamp1, time_format)
    t2 = datetime.datetime.strptime(timestamp2, time_format)
    difference = t2 - t1
    return difference.days, difference.total_seconds()

# Function to get uptime
'''def get_uptime(pid):
    with open(f'/proc/{pid}/stat', 'r') as f:
        fields = f.readline().split()
        start_time = int(fields[21]) / os.sysconf(os.sysconf_names['SC_CLK_TCK'])
        uptime_seconds = time.time() - start_time
        return datetime.timedelta(seconds=uptime_seconds)
'''

def get_uptime(pid):
    process = psutil.Process(pid)
    uptime_seconds = time.time() - process.create_time()
    return datetime.timedelta(seconds=uptime_seconds)

# Function to get memory usage
def get_memory_usage():
    mem_info = subprocess.run(['free', '-m'], stdout=subprocess.PIPE).stdout.decode().splitlines()[1]
    total_memory, used_memory, free_memory, _, _, available_memory = map(int, mem_info.split()[1:])
    used_memory_percentage = (used_memory / total_memory) * 100
    return used_memory_percentage, available_memory

# Function to get CPU usage
def get_cpu_usage():
    num_cores = os.cpu_count()
    load_avg = os.getloadavg()
    five_minute_util = (load_avg[1] / num_cores) * 100
    cpu_usage = subprocess.run(['top', '-bn1'], stdout=subprocess.PIPE).stdout.decode()
    cpu_usage = 100.0 - float(re.search(r'\d+\.\d+ id', cpu_usage).group().split()[0])
    return cpu_usage, five_minute_util

# Function to get temperature
def get_temperature():
    temp = subprocess.run(['vcgencmd', 'measure_temp'], stdout=subprocess.PIPE).stdout.decode()
    temp = float(re.search(r'[\d.]+', temp).group())
    return temp

# Function to get disk usage
def get_disk_usage(disk_path):
    disk_details = subprocess.run(['df', '-h', disk_path], stdout=subprocess.PIPE).stdout.decode().splitlines()[1]
    percent_full = int(disk_details.split()[4].rstrip('%'))
    space_remaining = disk_details.split()[3]
    return percent_full, space_remaining

# Function to check directory readability
def check_directory(directory):
    return os.access(directory, os.R_OK)

# Function to get AOTD date and value
def get_aotd(aotd_file):
    with open(aotd_file, 'r') as file:
        last_line = file.readlines()[-1]
    formatted_date = f"{last_line[:4]}-{last_line[4:6]}-{last_line[6:8]}"
    third_value = last_line.split(',')[2]
    return formatted_date, third_value

# Function to get today's date
def get_today():
    response = subprocess.run(['curl', '-s', 'http://worldtimeapi.org/api/timezone/America/New_York'], stdout=subprocess.PIPE).stdout.decode()
    today = re.search(r'\d{4}-\d{2}-\d{2}', response).group()
    return today

def output(string=''):
    global OUTPUT_CONTENT
    OUTPUT_CONTENT += string + "\n"

# Main logic
if __name__ == "__main__":

    cpu_usage, five_minute_util = get_cpu_usage()
    temp = get_temperature()
    used_memory_percentage, available_memory = get_memory_usage()

    process_name = "audioalchemy"
    process_lines = check_process(process_name)
    line_count = len(process_lines)
    pid = int(process_lines[0].split()[0]) if line_count > 0 and process_lines[0] else None

    #pid = int(process_lines[0].split()[0]) if line_count >= 1 else None

    log_file_path = './logs/errors.log'
    if not os.path.exists(log_file_path):
        output(f"{RED}Error: Log file {log_file_path} does not exist.{NC}")
        exit(1)

    last_timestamp = get_last_error_timestamp(log_file_path)
    if not last_timestamp:
        output(f"{RED}Error: No valid timestamp found in the log file.{NC}")
        exit(1)


    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    days_difference, seconds_difference = calculate_days_difference(last_timestamp, current_time)

    if pid:
        uptime = get_uptime(pid)


        # Extract days, hours, minutes, and seconds
        days = uptime.days
        hours, remainder = divmod(uptime.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)

        # Format the uptime into a readable string
        uptime_formatted_output = f"{days} days, {hours} hr, {minutes} min, {seconds} sec"
        #uptime_formatted_output = str(uptime)


    if "-f" in os.sys.argv:
        output("\n\n\n")
        output("##########################################")
        output("##                                      ##")
        output("##            Error Log                 ##")
        output("##                                      ##")
        output("##########################################\n")
        with open(log_file_path, 'r') as file:
            lines = file.readlines()
            for line in lines[-80:]:
                output(line)


    ##########################################
    ###             Uptime
    ##########################################

    output("\n")

    if line_count >= 1:
        output(f"Alchemy status: {GREEN}ON{NC}  {GREY}{uptime_formatted_output}{NC}")
    else:
        output(f"Alchemy is {RED}OFF{NC}")

    if "-f" in os.sys.argv:
        output(f"\nPid: {GREEN}{pid}{NC}")

    output()

    ##########################################
    ###             ERROR LOG
    ##########################################
    if last_timestamp:
        last_error_time = datetime.datetime.strptime(last_timestamp, "%Y-%m-%d %H:%M:%S")
        current_time = datetime.datetime.now()
        time_difference = current_time - last_error_time

        if time_difference.total_seconds() <= 24.5 * 3600:
            output(f"Last error: {RED}{last_timestamp}{NC}")
        else:
            days_difference, _ = calculate_days_difference(last_timestamp, current_time.strftime("%Y-%m-%d %H:%M:%S"))
            output(f"Last error: {GREEN}{days_difference} days ago{NC}  {GREY}{last_timestamp}{NC}")
    else:
        output(f"{RED}Error: No valid timestamp found in the log file.{NC}")
  
        
    


    used_memory_percentage, available_memory = get_memory_usage()
    available_memory = available_memory / 1024
    color = GREEN if used_memory_percentage < 30.0 else RED
    output(f"\nMemory Usage: {color}{used_memory_percentage:.1f}%{NC}  {GREY}{available_memory:.2}GB free{NC}")

    ##########################################
    ###             CPU
    ##########################################    
    
    max_now = 45.0
    max_average = 10.0

    cpu_output = ''
    
    if (five_minute_util < max_average):
        color = GREEN
    else:
        color = RED
    cpu_output += f"CPU Usage: {color}{five_minute_util:.1f}%{NC}{GREY} five min avg  --  {NC}"
    


    if (cpu_usage < max_now):
        color = GREEN
    else:
        color = RED
    cpu_output += f" {color}{cpu_usage:.1f}%{NC}{GREY} now{NC}"
    
    output()
    output(cpu_output)

    
    color = RED if temp > 47 else GREEN
    output(f"\nTemp: {color}{temp}{NC}")

    percent_full, space_remaining = get_disk_usage('/mnt/audioalchemy')
    color = GREEN if percent_full < 85 else RED
    output(f"\nLibrary: {color}{percent_full}% full{NC}  {GREY}{space_remaining}B available{NC}")

    aotd_file = '/mnt/audioalchemy/dbcache/aotdcache.csv'
    formatted_date, third_value = get_aotd(aotd_file)
    today = get_today()
    if formatted_date != today:
        color = RED
        message = " AOTD is out of date."
    else:
        color = GREEN
        message = ""
    output(f"\nAOTD: {color}{formatted_date}{message}{NC}  {GREY}{third_value}{NC}")
    output()
    print(OUTPUT_CONTENT)
