import requests
import warnings
import time

warnings.filterwarnings("ignore", message="Unverified HTTPS request")

class DiskPublish:
    def __init__(self, vbr_server, target_server, VMname, token, number_of_rp, description):
        self.vbr_server = vbr_server
        self.target_server = target_server
        self.vm_name = VMname
        self.token = token
        self.number_of_rp = number_of_rp
        self.description = description
    
    def get_headers(self):
        headers = {
            'Authorization': f'Bearer {self.token}', 
            'x-api-version': '1.2-rev0'
        }
        return headers

    def get_credential_id(self):
        url = f'{self.vbr_server}/api/v1/credentials'
        headers = self.get_headers()
        payload = {
            "typeFilter": "Linux",
        }
        response = requests.get(url, headers=headers, params=payload, verify=False)
        response.raise_for_status()
        cred_id = [item for item in response.json()['data'] if item['description'] == self.description][0]['id']
        return cred_id

    def get_restore_points(self):
        url = f'{self.vbr_server}/api/v1/restorePoints'
        headers = self.get_headers()
        payload = {
            'nameFilter': self.vm_name,
            'limit': self.number_of_rp
        }
        response = requests.get(url, headers=headers, params=payload, verify=False)
        response.raise_for_status()
        return response.json()
    
    def start_publish(self, rp_id):
        url = f'{self.vbr_server}/api/v1/dataIntegration/publish'
        headers = self.get_headers()
        payload = {
            "restorePointId": rp_id,
            "type": "FUSELinuxMount",
            "targetServerName": self.target_server,
            "targetServerCredentialsId": self.get_credential_id()
        }
        response = requests.post(url, json=payload, headers=headers, verify=False)
        response.raise_for_status()
        return response.json()['id']
    
    def check_publish(self, mountId):
        url = f'{self.vbr_server}/api/v1/dataIntegration/{mountId}'
        headers = self.get_headers()
        response = requests.get(url, headers=headers, verify=False)
        response.raise_for_status()
        return response.json()['mountState']
    
    def stop_publish(self, mountId):
        url = f'{self.vbr_server}/api/v1/dataIntegration/{mountId}/unpublish'
        headers = self.get_headers()
        response = requests.post(url, headers=headers, verify=False)
        response.raise_for_status()

    def get_published_mount_points(self):
        url = f'{self.vbr_server}/api/v1/dataIntegration'
        headers = self.get_headers()
        response = requests.get(url, headers=headers, verify=False)
        response.raise_for_status()
        return response.json()['data']

    def get_restore_points_created_time(self, rp_id):
        url = f'{self.vbr_server}/api/v1/restorePoints/{rp_id}'
        headers = self.get_headers()
        response = requests.get(url, headers=headers, verify=False)
        response.raise_for_status()
        return response.json()['creationTime']
    
    def process_restore_point(self, target_path):
        rp_ids = self.get_restore_points()
        for rp in rp_ids['data']:
            self.start_publish(rp['id'])
        time.sleep(10)

        all_mounted = self.get_published_mount_points()
        mount_ids = [mounted['id'] for mounted in all_mounted]

        self.wait_until_all_working(mount_ids)

        all_mounted = self.get_published_mount_points()
        results = self.extract_results(all_mounted, target_path)
        return results
    
    def wait_until_all_working(self, mount_ids):
        while True:
            statuses = [self.check_publish(id) for id in mount_ids]
            if all(status == 'Mounted' for status in statuses):
                break
            time.sleep(5)

    def extract_results(self, all_mounted, target_path):
        results = []
        mp = None
        for mounted in all_mounted:
            id = mounted['id']
            info = mounted['info']
            vmName = mounted['restorePointName']
            restore_point_id = mounted['restorePointId']
            createdTime = self.get_restore_points_created_time(restore_point_id)
            backupName = mounted['backupName']
            disks = info['disks']
            for disk in disks:
                mountpoints = disk['mountPoints']
                for mountpoint in mountpoints:
                    if mountpoint.endswith(target_path):
                        mp = mountpoint
            results.append({"id": id, "vmName": vmName, "backupName": backupName, "creationTime": createdTime, "mountPoint": mp})
        return results
    
    def cleanup_mounts(self, results):
        for mount in results:
            self.stop_publish(mount['id'])
