import requests
import os
import sys
import time

# Vultr API Endpoint
API_BASE = "https://api.vultr.com/v2"

def deploy_server(api_key, ssh_key_path, label="elasticseer-backend"):
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    # 1. Read SSH Key
    try:
        with open(ssh_key_path, 'r') as f:
            ssh_key_content = f.read().strip()
    except Exception as e:
        print(f"❌ Error reading SSH key: {e}")
        return

    # 2. Add SSH Key to Vultr if not exists (or just use it)
    print("🔑 Registering SSH key with Vultr...")
    ssh_data = {
        "name": "ElasticSeerKey",
        "ssh_key": ssh_key_content
    }
    ssh_resp = requests.post(f"{API_BASE}/ssh-keys", headers=headers, json=ssh_data)
    
    ssh_key_id = ""
    if ssh_resp.status_code == 201:
        ssh_key_id = ssh_resp.json()["ssh_key"]["id"]
        print(f"✅ SSH Key registered: {ssh_key_id}")
    else:
        # Maybe it already exists? List them.
        list_resp = requests.get(f"{API_BASE}/ssh-keys", headers=headers)
        ssh_keys = list_resp.json().get("ssh_keys", [])
        for k in ssh_keys:
            if k["ssh_key"] == ssh_key_content:
                ssh_key_id = k["id"]
                print(f"✅ Using existing SSH Key: {ssh_key_id}")
                break
        
        if not ssh_key_id:
            print(f"❌ Failed to register SSH key: {ssh_resp.text}")
            return

    # 3. Create the Instance
    # Region: sjc (Silicon Valley)
    # Plan: vc2-1c-1gb ($6/mo)
    # OS: 1743 (Ubuntu 22.04 x64)
    print("🚀 Provisioning Vultr instance (Ubuntu 22.04, $6/mo)...")
    instance_data = {
        "region": "sjc",
        "plan": "vc2-1c-1gb",
        "os_id": 1743,
        "label": label,
        "sshkey_id": [ssh_key_id],
        "backups": "disabled"
    }
    
    inst_resp = requests.post(f"{API_BASE}/instances", headers=headers, json=instance_data)
    if inst_resp.status_code != 202:
        print(f"❌ Failed to create instance: {inst_resp.text}")
        return
    
    instance = inst_resp.json()["instance"]
    instance_id = instance["id"]
    print(f"✅ Instance creation triggered! ID: {instance_id}")

    # 4. Wait for IP address
    print("⏳ Waiting for IP address assignment...")
    ip_address = ""
    for _ in range(20):
        time.sleep(10)
        status_resp = requests.get(f"{API_BASE}/instances/{instance_id}", headers=headers)
        inst_details = status_resp.json()["instance"]
        ip_address = inst_details.get("main_ip")
        if ip_address and ip_address != "0.0.0.0":
            break
        print("  ...still waiting...")

    if ip_address:
        print(f"\n✨ SUCCESS! SERVER IS UP! ✨")
        print(f"🌐 IP Address: {ip_address}")
        print(f"--------------------------------------------------------")
        print(f"Next Steps:")
        print(f"1. Wait a 1-2 minutes for Ubuntu to finish booting.")
        print(f"2. SSH into your server: ssh root@{ip_address}")
        print(f"3. Run the setup commands I provided in the guide.")
        print(f"--------------------------------------------------------")
    else:
        print(f"❌ Timeout waiting for IP. Check your Vultr dashboard.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python deploy_vultr_api.py <VULTR_API_KEY>")
        sys.exit(1)
    
    api_key = sys.argv[1]
    ssh_path = os.path.expanduser("~/.ssh/id_rsa.pub")
    deploy_server(api_key, ssh_path)
