# encoding=utf8
import io
import re
import sys
import requests  # 新增requests库
sys.stdout = io.TextIOWrapper(sys.stdout.buffer,encoding='utf-8')

import undetected_chromedriver as uc
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By

# 新增钉钉通知函数
def send_dingtalk_notification(webhook_url, message):
    headers = {"Content-Type": "application/json"}
    data = {
        "msgtype": "text",
        "text": {
            "content": f"ZodGame自动任务通知\n{message}"
        }
    }
    try:
        resp = requests.post(webhook_url, json=data, headers=headers, timeout=10)
        print("【通知】钉钉消息发送状态:", resp.status_code)
    except Exception as e:
        print("【通知】钉钉消息发送失败:", str(e))

def zodgame_checkin(driver, formhash):
    checkin_url = "https://zodgame.xyz/plugin.php?id=dsu_paulsign:sign&operation=qiandao&infloat=1&inajax=0"    
    checkin_query = """
        (function (){
        var request = new XMLHttpRequest();
        var fd = new FormData();
        fd.append("formhash","%s");
        fd.append("qdxq","kx");
        request.open("POST","%s",false);
        request.withCredentials=true;
        request.send(fd);
        return request;
        })();
        """ % (formhash, checkin_url)
    checkin_query = checkin_query.replace("\n", "")
    driver.set_script_timeout(240)
    resp = driver.execute_script("return " + checkin_query)
    match = re.search('<div class="c">\r\n(.*?)</div>\r\n', resp["response"], re.S)
    message = match[1] if match is not None else "签到失败"
    print(f"【签到】{message}")
    success = "恭喜你签到成功!" in message or "您今日已经签到，请明天再来" in message
    return success, message  # 返回更详细的信息

def zodgame_task(driver, formhash):
    def clear_handles(driver, main_handle):
        handles = driver.window_handles[:]
        for handle in handles:
            if handle != main_handle:
                driver.switch_to.window(handle)
                driver.close()
        driver.switch_to.window(main_handle)
      
    def show_task_reward(driver):
        driver.get("https://zodgame.xyz/plugin.php?id=jnbux")
        try:
            WebDriverWait(driver, 240).until(
                lambda x: x.title != "Just a moment..."
            )
            reward = driver.find_element(By.XPATH, '//li[contains(text(), "点币: ")]').get_attribute("textContent")[:-2]
            print(f"【Log】{reward}")
            return reward
        except:
            return "未获取到奖励信息"

    driver.get("https://zodgame.xyz/plugin.php?id=jnbux")
    WebDriverWait(driver, 240).until(
        lambda x: x.title != "Just a moment..."
    )

    join_bux = driver.find_elements(By.XPATH, '//font[text()="开始参与任务"]')
    if len(join_bux) != 0 :    
        driver.get(f"https://zodgame.xyz/plugin.php?id=jnbux:jnbux&do=join&formhash={formhash}")
        WebDriverWait(driver, 240).until(
            lambda x: x.title != "Just a moment..."
        )
        driver.get("https://zodgame.xyz/plugin.php?id=jnbux")
        WebDriverWait(driver, 240).until(
            lambda x: x.title != "Just a moment..."
        )

    join_task_a = driver.find_elements(By.XPATH, '//a[text()="参与任务"]')
    success = True
    task_results = []

    if len(join_task_a) == 0:
        msg = "所有任务均已完成"
        print(f"【任务】{msg}")
        task_results.append(msg)
        return success, task_results

    handle = driver.current_window_handle
    for idx, a in enumerate(join_task_a):
        on_click = a.get_attribute("onclick")
        try:
            function = re.search("""openNewWindow(.*?)\(\)""", on_click, re.S)[0]
            script = driver.find_element(By.XPATH, f'//script[contains(text(), "{function}")]').get_attribute("text")
            task_url = re.search("""window.open\("(.*)", "newwindow"\)""", script, re.S)[1]
            driver.execute_script(f"""window.open("https://zodgame.xyz/{task_url}")""")
            driver.switch_to.window(driver.window_handles[-1])
            try:
                WebDriverWait(driver, 240).until(
                    lambda x: x.find_elements(By.XPATH, '//div[text()="成功！"]')
                )
            except:
                print(f"【Log】任务 {idx+1} 广告页检查失败。")
                pass

            try:     
                check_url = re.search("""showWindow\('check', '(.*)'\);""", on_click, re.S)[1]
                driver.get(f"https://zodgame.xyz/{check_url}")
                WebDriverWait(driver, 240).until(
                    lambda x: len(x.find_elements(By.XPATH, '//p[contains(text(), "检查成功, 积分已经加入您的帐户中")]')) != 0 
                        or x.title == "BUX广告点击赚积分 - ZodGame论坛 - Powered by Discuz!"
                )
            except:
                print(f"【Log】任务 {idx+1} 确认页检查失败。")
                pass

            task_results.append(f"任务 {idx+1} 成功")
            print(f"【任务】任务 {idx+1} 成功。")
        except Exception as e:
            success = False
            task_results.append(f"任务 {idx+1} 失败 - {str(type(e))}")
            print(f"【任务】任务 {idx+1} 失败。", type(e))
        finally:
            clear_handles(driver, handle)
    
    reward = show_task_reward(driver)
    task_results.append(f"当前点币: {reward}")

    return success, "\n".join(task_results)  # 返回任务详情

def zodgame(cookie_string, webhook_url=None):  # 新增webhook参数
    options = uc.ChromeOptions()
    options.add_argument("--disable-popup-blocking")
    driver = uc.Chrome(driver_executable_path = """C:\SeleniumWebDrivers\ChromeDriver\chromedriver.exe""",
                       browser_executable_path = """C:\Program Files\Google\Chrome\Application\chrome.exe""",
                       options = options)

    # Load cookie
    driver.get("https://zodgame.xyz/")

    if cookie_string.startswith("cookie:"):
        cookie_string = cookie_string[len("cookie:"):]
    cookie_string = cookie_string.replace("/","%2")
    cookie_dict = [ 
        {"name" : x.split('=')[0].strip(), "value": x.split('=')[1].strip()} 
        for x in cookie_string.split(';')
    ]

    driver.delete_all_cookies()
    for cookie in cookie_dict:
        if cookie["name"] in ["qhMq_2132_saltkey", "qhMq_2132_auth"]:
            driver.add_cookie({
                "domain": "zodgame.xyz",
                "name": cookie["name"],
                "value": cookie["value"],
                "path": "/",
            })
    
    driver.get("https://zodgame.xyz/")
    
    WebDriverWait(driver, 240).until(
        lambda x: x.title != "Just a moment..."
    )
    assert len(driver.find_elements(By.XPATH, '//a[text()="用户名"]')) == 0, "Login fails. Please check your cookie."
        
    formhash = driver.find_element(By.XPATH, '//input[@name="formhash"]').get_attribute('value')
    
    # 获取任务结果
    checkin_success, checkin_msg = zodgame_checkin(driver, formhash)
    task_success, task_msg = zodgame_task(driver, formhash)
    
    # 构建通知消息
    final_msg = []
    final_msg.append(f"签到结果: {checkin_msg}")
    final_msg.append(f"任务详情:\n{task_msg}")
    final_msg = "\n".join(final_msg)
    
    # 发送钉钉通知
    if webhook_url:
        send_dingtalk_notification(webhook_url, final_msg)
    else:
        print("【通知】未提供钉钉Webhook URL，跳过通知")

    assert checkin_success and task_success, "Checkin failed or task failed."

    driver.close()
    driver.quit()
    
if __name__ == "__main__":
    cookie_string = sys.argv[1]
    webhook_url = sys.argv[2] if len(sys.argv) > 2 else None  # 新增第二个参数
    assert cookie_string
    
    zodgame(cookie_string, webhook_url)
