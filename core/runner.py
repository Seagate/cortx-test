import json


def parse_json(json_file) :
    """
    Parse given json file
    """
    with open(json_file, "r") as read_file :
        json_dict = json.load(read_file)

    cmd = ''
    run_using = ''
    # Execution priority is given to test name first then to file name and at last to tag.
    if json_dict['test_name'] != '' :
        cmd = json_dict['test_name']
        run_using = 'test_name'
    elif json_dict['file_name'] != '' :
        cmd = json_dict['file_name']
        run_using = 'file_name'
    elif json_dict['tag'] != '' :
        cmd = json_dict['tag']
        run_using = 'tag'
    return json_dict, cmd, run_using


def get_cmd_line(cmd, run_using, html_report, log_cli_level) :
    if run_using == 'tag' :
        cmd = '-m ' + cmd
    result_html_file = '--html={}'.format(html_report)
    log_cli_level_str = '--log-cli-level={}'.format(log_cli_level)
    cmd_line = ['pytest', log_cli_level_str, result_html_file, cmd]
    return cmd_line


