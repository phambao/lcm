from celery import shared_task
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.mail import send_mail
from django.http import HttpRequest
from django.core.files.base import ContentFile

from api.middleware import set_request
from api.models import ActivityLog
from base.models.config import FileBuilder365
from base.utils import str_to_class
from sales.models import Catalog
from openpyxl.workbook import Workbook
from io import BytesIO
from celery import current_task
from datetime import datetime


@shared_task()
def process_export_catalog(pk, company, user_id):
    workbook = Workbook()
    task_id = current_task.request.id
    if pk is None:
        data_catalog = Catalog.objects.filter(is_ancestor=True, parents=None, company=company)
        for catalog in data_catalog:
            child_catalogs = Catalog.objects.filter(parents=catalog.id)
            for data_catalog in child_catalogs:
                handle_export(data_catalog.id, workbook, catalog.name)

    else:
        check_catalog = Catalog.objects.get(id=pk)
        if check_catalog.is_ancestor:
            child_catalogs = Catalog.objects.filter(parents=pk)
            for data_catalog in child_catalogs:
                handle_export(data_catalog.id, workbook, check_catalog.name)

        else:
            handle_export(pk, workbook, '')

    bytes_io = BytesIO()
    workbook.save(bytes_io)
    bytes_io.seek(0)

    content = ContentFile(bytes_io.read())
    content.seek(0)

    attachment = FileBuilder365()
    user = get_user_model().objects.get(pk=user_id)
    request = HttpRequest()
    request.user = user
    set_request(request)

    current_datetime = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"catalog_{current_datetime}.xlsx"
    attachment.file.save(filename, content)
    attachment.size = content.size
    attachment.name = filename
    attachment.task_id = task_id
    attachment.save()


def handle_export(pk, workbook, sheet_name):
    root_catalogs = Catalog.objects.filter(id=pk)
    all_paths = []
    name = root_catalogs.first().name
    level = Catalog.objects.get(id=pk).get_ordered_levels()
    # get all path catalog to cost table
    for root_catalog in root_catalogs:
        find_all_paths(root_catalog, [], all_paths)

    # get all data point with catalog on path
    rs = []
    for path in all_paths:
        temp = list()
        temp_catalog_not_dtp = list()
        for idx, data in enumerate(path):
            if isinstance(data, list):
                temp.append(data)
                temp_catalog_not_dtp.append(data)
            elif isinstance(data, Catalog):
                tmp = list()
                if data.data_points.exists():
                    temp_list = []
                    for data_point in data.data_points.all():
                        temp_list.append(data.name)
                        temp_list.append(data.icon)
                        if data_point.unit:
                            temp_list.append(data_point.unit.name)
                        else:
                            temp_list.append('')
                        temp_list.append(data_point.value)
                        temp_list.append(data_point.linked_description)
                        tmp.append(temp_list)
                        temp_list = []
                        if idx != 0 and len(path) == 2:
                            temp_catalog_not_dtp.append([data.id])
                    temp.append(tmp)
                else:
                    if idx != 0:
                        temp.append([data.id])
                        temp_catalog_not_dtp.append([data.id])
        if temp == []:
            rs.append(temp_catalog_not_dtp)

        elif len(temp) == 1 and isinstance(temp[0], list):
            rs.append(temp_catalog_not_dtp)
        else:
            rs.append(temp)

    # get all path with data point
    result_paths = []
    for i in rs:
        generate_paths(i, [], result_paths)

    # handle write headers all catalog and cost table
    # workbook = Workbook()
    data_sheet_name = sheet_name + '-' + name
    data_sheet_name = data_sheet_name.replace("/", "-")
    catalog_sheet = workbook.create_sheet(title=data_sheet_name)
    headers = []
    for i in range(1, len(level) + 1):
        data_level = level[i - 1]
        iteration_headers = [f"{data_level.name}", "image", f"value", f"unit", f"des"]
        headers.extend(iteration_headers)

    all_key = []
    for path in result_paths:
        for data in path:
            if isinstance(data, dict):
                for key in data.keys():
                    if key not in all_key:
                        all_key.append(key)
                break
    headers.extend(all_key)
    catalog_sheet.append(headers)

    # write all data into excel
    if len(level) > 0:
        for path in result_paths:
            number = len(level) * 5
            row = [""] * (number + len(all_key))
            for idx, data in enumerate(path):
                # write catalog data
                if isinstance(data, int):
                    data_catalog = Catalog.objects.get(id=data)
                    if idx == 0:
                        row[idx] = data_catalog.name
                        row[idx + 1] = data_catalog.icon
                    else:
                        row[idx * 5] = data_catalog.name
                        row[idx * 5 + 1] = data_catalog.icon

                elif isinstance(data, list):
                    if idx == 0:
                        row[idx] = data[0]
                        row[idx + 1] = data[1]
                        row[idx + 2] = data[2]
                        row[idx + 3] = data[3]
                        row[idx + 4] = data[4]
                    else:
                        row[idx * 5] = data[0]
                        row[idx * 5 + 1] = data[1]
                        row[idx * 5 + 2] = data[2]
                        row[idx * 5 + 3] = data[3]
                        row[idx * 5 + 4] = data[4]
                # write cost table
                elif isinstance(data, dict):
                    temp_len = len(headers) - number
                    temp_length = headers[-temp_len:]
                    for index, header in enumerate(temp_length, number):
                        if header in data:
                            row[index] = data[header]
                        else:
                            row[index] = ""
                # write catalog not data point
                else:
                    if idx == 0:
                        row[idx] = data
                    else:
                        row[idx * 5] = data
            catalog_sheet.append(row)


def generate_paths(categories, current_path, result):
    if categories == []:
        current_category = categories
    elif isinstance(categories[0][0], dict):
        current_category = categories[0]

    elif isinstance(categories[0][0], list):
        current_category = categories[0]

    elif isinstance(categories[0][0], int):
        current_category = categories[0]

    else:
        current_category = set(categories[0])
    for item in current_category:
        new_path = current_path + [item]

        if len(categories) == 1:
            result.append(new_path)
        else:
            generate_paths(categories[1:], new_path, result)


def find_all_paths(node, current_path, all_paths):
    if node is None:
        return

    current_path.append(node)
    if not node.children.exists():
        path = list(current_path)
        if hasattr(node, 'c_table') and node.c_table:
            result_list = []
            headers = node.c_table['header']
            for row in node.c_table["data"]:
                result_dict = dict(zip(headers, row))
                result_list.append(result_dict)
            all_paths.append(path + [result_list])

        elif hasattr(node, 'c_table') and not node.c_table:
            # all_paths.append(path + [node.name])
            all_paths.append(path)
        current_path.pop()
    else:
        for child in node.children.all():
            find_all_paths(child, list(current_path), all_paths)

    if len(current_path) > 1:
        current_path.pop()

@shared_task()
def celery_send_mail(subject, message, from_email, recipient_list,
                     fail_silently=False, auth_user=None, auth_password=None,
                     connection=None, html_message=None):
    send_mail(subject, message, from_email, recipient_list,
              fail_silently=fail_silently, auth_user=auth_user, auth_password=auth_password,
              connection=connection, html_message=html_message)


@shared_task()
def activity_log(model, instance, action, serializer_name, base_import_file, user_id):
    """
    Parameters:
        model: int
        instance: pk
        action: int
        serializer_name: str
        base_import_file: str
    """
    user = get_user_model().objects.get(pk=user_id)
    request = HttpRequest()
    request.user = user
    set_request(request)

    content_type = ContentType.objects.get_for_id(model)
    model_class = content_type.model_class()
    instance = model_class.objects.get(pk=instance)
    serializer = str_to_class(base_import_file, serializer_name)
    data = serializer(instance).data
    ActivityLog.objects.create(content_type=content_type, content_object=instance, object_id=instance.pk,
                               action=action, last_state=data, next_state={})
