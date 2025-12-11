from django.shortcuts import render
import requests
import re
from bs4 import BeautifulSoup
from django.http import HttpResponse
import concurrent.futures
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .ReadMailBox import ReadMailBox
import json


def home_view(request):
    return render(request, 'home.html')

def get_code_view(request):
    try:
        if request.method == 'POST':
            email_data = request.POST.get('email_data', '')
            results_list = []
            if email_data:
                email_data_parse = parse_multiple_data(email_data)
                if email_data_parse is None or not isinstance(email_data_parse, list) or len(email_data_parse) == 0:
                    return render(request, 'home.html')
                # Remove duplicate emails while preserving the latest data for each email
                unique_emails = {}
                for email in email_data_parse:
                    email_address = email.get('email', '')
                    if email_address:
                        unique_emails[email_address] = email
                # Create a ThreadPoolExecutor with max_workers parameter
                max_threads = min(32, len(unique_emails))
                with concurrent.futures.ThreadPoolExecutor(max_workers=max_threads) as executor:
                    # socket_id = request.POST.get('socket_id')
                    future_to_email = {}
                    for email in unique_emails.values():
                        future = executor.submit(read_mail, email['email'], email['additional_info'], email['id'], email['index'], request)
                        future_to_email[future] = email['email']
                    # Process results as they complete
                    for future in concurrent.futures.as_completed(future_to_email):
                        email_user = future_to_email[future]
                        email_data = next((data for data in email_data_parse if data['email'] == email_user), None)
                        try:
                            results = future.result()
                            if type(results) == list:
                                if results:  # Only add if there are results
                                    results_list.append({
                                        "email_user": {
                                            "address": email_user,
                                            "index": email_data['index'] if email_data else 0
                                        },
                                        "results": results
                                    })
                        except Exception as e:
                            results_list.append({
                                "email_user": {
                                    "address": email_user,
                                    "index": email_data['index'] if email_data else 0
                                },
                                "results": f"Error: {str(e)}"
                            })
                # Sort results_list by index before rendering
                results_list.sort(key=lambda x: x['email_user']['index'])
                return HttpResponse('Processing completed')
            return render(request, 'home.html')
        return render(request, 'home.html')
    except Exception as e:
        return render(request, 'home.html')

def parse_multiple_data(input_string):
    try:
        # Tách chuỗi theo dấu '\n' để lấy từng dòng
        lines = [line.strip() for line in input_string.split("\n") if line.strip()]  # Loại bỏ dòng trống
        result = []
        for index, line in enumerate(lines, 1):  # Bắt đầu đếm từ 1
            # Tách mỗi dòng theo dấu '|'
            attributes = line.split("|")
            # Kiểm tra đủ thông tin
            if len(attributes) >= 4:
                # Tạo dictionary cho mỗi đối tượng
                data_object = {
                    "index": index,  # Thêm số thứ tự
                    "email": attributes[0].strip(),
                    "password": attributes[1].strip(),
                    "additional_info": attributes[2].strip(),
                    "id": attributes[3].strip()
                }
                result.append(data_object)
        return result
    except Exception as e:
        return None

def read_mail(email, refresh_token, client_id, email_index, request):
    try:
        # Thử dùng Graph API trước
        try:
            results = read_mail_graph(email, refresh_token, client_id, email_index, request)
            if results and not isinstance(results, str) and len(results) > 0:
                return results
        except Exception:
            pass
        # Nếu không có kết quả hoặc lỗi, thử IMAP
        try:
            results = read_mail_imap(email, refresh_token, client_id, email_index, request)
            if results and not isinstance(results, str) and len(results) > 0:
                return results
        except Exception:
            pass
        # Nếu cả hai đều lỗi hoặc không có kết quả
    except Exception:
        return None

def read_mail_graph(email, refresh_token, client_id, email_index, request):
    try:
        # is_result = False
        reader = ReadMailBox(client_id, refresh_token, email)
        access_token = reader.GetAccessToken()
        if access_token == "ERROR":
            return "Không lấy được access token"
        headers = {
            "Authorization": f"Bearer {access_token}",
        }
        response = requests.get("https://graph.microsoft.com/v1.0/me/messages", headers=headers)
        data = response.json()
        socket_id = request.POST.get('socket_id')
        if response.status_code != 200:
            return response.status_code

        results = []
        for item in data['value']:
            if not isinstance(item, dict):
                continue
            if item['from']['emailAddress']['address'] == 'noreply@notifications.textnow.com':
                try:
                    code = parse_html_tf(item['body']['content'])
                    tn_from = 'noreply@notifications.textnow.com'
                    tn_data = item['sentDateTime']
                    result = {'from': tn_from, 'code': code, 'date': tn_data}
                    results.append(result)
                    # is_result = True
                    if (code is None):
                        link = parse_beautifulshop_tn(item['body']['content'])
                        tn_from = 'noreply@notifications.textnow.com'
                        tn_data = item['sentDateTime']
                        result = {'from': tn_from, 'link': link, 'date': tn_data}
                        results.append(result)
                        # is_result = True
                    # Send WebSocket update
                    channel_layer = get_channel_layer()
                    async_to_sync(channel_layer.group_send)(
                        f"client_{socket_id}",
                        {
                            'type': 'email_update',
                            'email': email,
                            'result': result,
                            'email_index': email_index,
                            'result_index': len(results)
                        }
                    )
                except Exception as e:
                    print('error:\n', e)
                    continue

            if item['from']['emailAddress']['address'] == 'info@info.textfree.us':
                try:
                    code = parse_html_tf(item['body']['content'])
                    tf_from = 'info@info.textfree.us'
                    tf_data = item['sentDateTime']
                    result = {'from': tf_from, 'code': code, 'date': tf_data}
                    results.append(result)
                    # is_result = True
                    # Send WebSocket update
                    channel_layer = get_channel_layer()
                    async_to_sync(channel_layer.group_send)(
                        f"client_{socket_id}",
                        {
                            'type': 'email_update',
                            'email': email,
                            'result': result,
                            'email_index': email_index,
                            'result_index': len(results)
                        }
                    )
                except Exception as e:
                    print('error:\n', e)
                    continue

        # if not is_result:
        #     result = {'from': email, 'code': 'No result', 'date': 'No result'}
        #     results.append(result)
        #     channel_layer = get_channel_layer()
        #     async_to_sync(channel_layer.group_send)(
        #         f"client_{socket_id}",
        #         {
        #             'type': 'email_update',
        #             'email': email,
        #             'result': result,
        #             'email_index': email_index,
        #             'result_index': len(results)
        #         }
        #     )
        return results
    except Exception as e:
        return f"An error occurred: {e}"

def read_mail_imap(email, refresh_token, client_id, email_index, request):
    try:
        is_result = False
        results = []
        url = "http://207.148.69.229:5000/api/mail/read"
        payload = {
            "Email": email,
            "RefreshToken": refresh_token,
            "ClientId": client_id
        }
        socket_id = request.POST.get('socket_id')
        response = requests.post(url, json=payload)
        if response.status_code != 200:
            result = {'from': 'No result', 'code': 'No result', 'date': 'No result'}
            results.append(result)
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f"client_{socket_id}",
                {
                    'type': 'email_update',
                    'email': email,
                    'result': result,
                    'email_index': email_index,
                    'result_index': len(results)
                }
            )
            return results

        data = response.json()
        for item in data:
            if not isinstance(item, dict):
                continue
            if item.get('from') == 'noreply@notifications.textnow.com':
                try:
                    link = parse_beautifulshop_tn(item.get('body', ''))
                    tn_from = item.get('from', '')
                    tn_data = item.get('date', '')
                    result = {'from': tn_from, 'link': link, 'date': tn_data}
                    results.append(result)
                    is_result = True
                    if (link is None):
                        code = parse_html_tf(item.get('body', ''))
                        tf_from = item.get('from', '')
                        tf_data = item.get('date', '')
                        result = {'from': tf_from, 'code': code, 'date': tf_data}
                        results.append(result)
                        is_result = True
                    # Send WebSocket update
                    channel_layer = get_channel_layer()
                    async_to_sync(channel_layer.group_send)(
                        f"client_{socket_id}",
                        {
                            'type': 'email_update',
                            'email': email,
                            'result': result,
                            'email_index': email_index,
                            'result_index': len(results)
                        }
                    )
                except Exception as e:
                    continue

            if item.get('from') == 'info@info.textfree.us':
                try:
                    code = parse_html_tf(item.get('body', ''))
                    tf_from = item.get('from', '')
                    tf_data = item.get('date', '')
                    result = {'from': tf_from, 'code': code, 'date': tf_data}
                    results.append(result)
                    is_result = True
                    # Send WebSocket update
                    channel_layer = get_channel_layer()
                    async_to_sync(channel_layer.group_send)(
                        f"client_{socket_id}",
                        {
                            'type': 'email_update',
                            'email': email,
                            'result': result,
                            'email_index': email_index,
                            'result_index': len(results)
                        }
                    )
                except Exception as e:
                    continue

            if not is_result:
                result = {'from': 'No result', 'code': 'No result', 'date': 'No result'}
                results.append(result)
                channel_layer = get_channel_layer()
                async_to_sync(channel_layer.group_send)(
                    f"client_{socket_id}",
                    {
                        'type': 'email_update',
                        'email': email,
                        'result': result,
                        'email_index': email_index,
                        'result_index': len(results)
                    }
                )
        return results
    except Exception as e:
        return f"An error occurred: {e}"

def parse_html_tf(html_content):
    try:
        # Sử dụng biểu thức chính quy để tìm 6 chữ số liên tiếp và loại trừ "000000"
        match = re.search(r'(?<!#)\b(?!000000\b)\d{6}\b', html_content)
        if match:
            return match.group()
        else:
            return None
    except Exception as e:
        return None

def parse_beautifulshop_tn(html_content):
    # Phân tích cú pháp HTML với BeautifulSoup
    soup = BeautifulSoup(html_content, 'html.parser')
    # Tìm tất cả các thẻ <a> có href chứa "https://94lr.adj.st/email_verification"
    links = soup.find_all('a', href=True)

    # Lọc các link có href đúng với mẫu cần tìm
    target_links = [link['href'] for link in links if 'https://94lr.adj.st/email_verification' in link['href']]

    # In tất cả các link tìm được
    for link in target_links:
        return link
    
def txt_write(data_list):
    with open("output.txt", "w", encoding="utf-8") as f:
        for index, item in enumerate(data_list, start=1):
            f.write(f"Email {index}:\n")
            f.write(f"From: {item.get('from', '')}\n")
            f.write(f"Subject: {item.get('subject', '')}\n")
            f.write(f"Date: {item.get('date', '')}\n")
            f.write("Body:\n")
            f.write(item.get("body", "") + "\n")
            f.write("=" * 50 + "\n\n")

def txt_write_full(data, filename="graph_response.txt"):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)