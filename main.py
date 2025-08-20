#!/usr/bin/env python3
"""
Android Device Health & Performance Automation Suite
Author: [Your Name]
Description: Comprehensive Android device testing and health monitoring tool
"""

import subprocess
import json
import time
import os
import sys
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import re

class AndroidDeviceManager:
    """Core class for Android device management and testing"""
    
    def __init__(self):
        self.device_id = None
        self.test_results = {}
        self.start_time = datetime.now()
        
    def check_adb_connection(self) -> bool:
        """Check if ADB is properly installed and accessible"""
        try:
            result = subprocess.run(['adb', 'version'], capture_output=True, text=True)
            if result.returncode == 0:
                print("✅ ADB connection verified")
                return True
            return False
        except FileNotFoundError:
            print("❌ ADB not found. Please install Android SDK Platform Tools")
            return False
    
    def get_connected_devices(self) -> List[str]:
        """Get list of connected Android devices"""
        try:
            result = subprocess.run(['adb', 'devices'], capture_output=True, text=True)
            lines = result.stdout.strip().split('\n')[1:]  # Skip header
            devices = []
            for line in lines:
                if '\tdevice' in line:
                    device_id = line.split('\t')[0]
                    devices.append(device_id)
            return devices
        except Exception as e:
            print(f"❌ Error getting devices: {e}")
            return []
    
    def select_device(self) -> bool:
        """Select device for testing"""
        devices = self.get_connected_devices()
        if not devices:
            print("❌ No devices connected. Please connect an Android device with USB debugging enabled.")
            return False
        
        if len(devices) == 1:
            self.device_id = devices[0]
            print(f"✅ Using device: {self.device_id}")
        else:
            print("Multiple devices found:")
            for i, device in enumerate(devices):
                print(f"{i+1}. {device}")
            choice = input("Select device (1-{}): ".format(len(devices)))
            try:
                self.device_id = devices[int(choice)-1]
                print(f"✅ Selected device: {self.device_id}")
            except (ValueError, IndexError):
                print("❌ Invalid selection")
                return False
        return True
    
    def run_adb_command(self, command: str) -> Tuple[bool, str]:
        """Execute ADB command and return success status and output"""
        try:
            if self.device_id:
                cmd = ['adb', '-s', self.device_id] + command.split()
            else:
                cmd = ['adb'] + command.split()
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            return result.returncode == 0, result.stdout.strip()
        except subprocess.TimeoutExpired:
            return False, "Command timeout"
        except Exception as e:
            return False, str(e)

class DeviceHealthTester(AndroidDeviceManager):
    """Advanced device health testing capabilities"""
    
    def get_device_info(self) -> Dict:
        """Get comprehensive device information"""
        print("📱 Gathering device information...")
        info = {}
        
        # Basic device info
        commands = {
            'model': 'shell getprop ro.product.model',
            'brand': 'shell getprop ro.product.brand',
            'android_version': 'shell getprop ro.build.version.release',
            'sdk_version': 'shell getprop ro.build.version.sdk',
            'serial': 'shell getprop ro.serialno',
            'manufacturer': 'shell getprop ro.product.manufacturer'
        }
        
        for key, command in commands.items():
            success, output = self.run_adb_command(command)
            info[key] = output if success else "Unknown"
        
        self.test_results['device_info'] = info
        print("✅ Device information collected")
        return info
    
    def test_battery_health(self) -> Dict:
        """Test battery health and charging status"""
        print("🔋 Testing battery health...")
        battery_info = {}
        
        success, output = self.run_adb_command('shell dumpsys battery')
        if success:
            lines = output.split('\n')
            for line in lines:
                if 'level:' in line:
                    battery_info['level'] = line.split(':')[1].strip()
                elif 'health:' in line:
                    battery_info['health'] = line.split(':')[1].strip()
                elif 'status:' in line:
                    battery_info['status'] = line.split(':')[1].strip()
                elif 'temperature:' in line:
                    temp = line.split(':')[1].strip()
                    battery_info['temperature'] = f"{int(temp)/10}°C"
                elif 'voltage:' in line:
                    battery_info['voltage'] = line.split(':')[1].strip()
        
        # Battery capacity test
        success, capacity = self.run_adb_command('shell cat /sys/class/power_supply/battery/capacity')
        if success:
            battery_info['capacity'] = f"{capacity}%"
        
        self.test_results['battery'] = battery_info
        print("✅ Battery health test completed")
        return battery_info
    
    def test_storage_health(self) -> Dict:
        """Test storage capacity and health"""
        print("💾 Testing storage health...")
        storage_info = {}
        
        success, output = self.run_adb_command('shell df /data')
        if success:
            lines = output.split('\n')
            if len(lines) > 1:
                parts = lines[1].split()
                if len(parts) >= 4:
                    total = int(parts[1]) / 1024 / 1024  # Convert to GB
                    used = int(parts[2]) / 1024 / 1024
                    available = int(parts[3]) / 1024 / 1024
                    
                    storage_info['total_gb'] = f"{total:.2f} GB"
                    storage_info['used_gb'] = f"{used:.2f} GB"
                    storage_info['available_gb'] = f"{available:.2f} GB"
                    storage_info['usage_percent'] = f"{(used/total)*100:.1f}%"
        
        self.test_results['storage'] = storage_info
        print("✅ Storage health test completed")
        return storage_info
    
    def test_connectivity(self) -> Dict:
        """Test WiFi, Bluetooth, and mobile connectivity"""
        print("📡 Testing connectivity features...")
        connectivity = {}
        
        # WiFi test
        success, wifi_output = self.run_adb_command('shell dumpsys wifi')
        if success:
            connectivity['wifi_enabled'] = 'Wi-Fi is enabled' in wifi_output
            # Extract current WiFi network if connected
            if 'SSID:' in wifi_output:
                for line in wifi_output.split('\n'):
                    if 'SSID:' in line and not line.strip().endswith('SSID:'):
                        connectivity['current_wifi'] = line.split('SSID:')[1].strip()
                        break
        
        # Bluetooth test
        success, bt_output = self.run_adb_command('shell dumpsys bluetooth_manager')
        if success:
            connectivity['bluetooth_enabled'] = 'enabled: true' in bt_output.lower()
        
        # Mobile data test
        success, mobile_output = self.run_adb_command('shell dumpsys telephony.registry')
        if success:
            connectivity['mobile_data'] = 'DATA_CONNECTED' in mobile_output
        
        # Airplane mode check
        success, airplane = self.run_adb_command('shell settings get global airplane_mode_on')
        if success:
            connectivity['airplane_mode'] = airplane == '1'
        
        self.test_results['connectivity'] = connectivity
        print("✅ Connectivity test completed")
        return connectivity
    
    def test_camera_functionality(self) -> Dict:
        """Test camera module functionality"""
        print("📸 Testing camera functionality...")
        camera_info = {}
        
        # Check if camera app exists and can be launched
        success, output = self.run_adb_command('shell pm list packages | grep camera')
        camera_info['camera_app_available'] = success and 'camera' in output
        
        # Test camera service
        success, camera_service = self.run_adb_command('shell dumpsys media.camera')
        if success:
            camera_info['camera_service_active'] = 'Camera service is running' in camera_service or len(camera_service) > 0
            
            # Count available cameras
            camera_count = camera_service.count('Camera ')
            camera_info['available_cameras'] = camera_count
        
        # Test camera permissions
        success, perms = self.run_adb_command('shell dumpsys package com.android.camera | grep CAMERA')
        if success:
            camera_info['camera_permissions'] = 'granted' in perms.lower()
        
        self.test_results['camera'] = camera_info
        print("✅ Camera functionality test completed")
        return camera_info
    
    def test_performance_metrics(self) -> Dict:
        """Test device performance metrics"""
        print("⚡ Testing performance metrics...")
        performance = {}
        
        # CPU information
        success, cpu_info = self.run_adb_command('shell cat /proc/cpuinfo')
        if success:
            cpu_cores = cpu_info.count('processor')
            performance['cpu_cores'] = cpu_cores
            
            # Extract CPU model
            for line in cpu_info.split('\n'):
                if 'model name' in line.lower():
                    performance['cpu_model'] = line.split(':')[1].strip()
                    break
        
        # Memory information
        success, mem_info = self.run_adb_command('shell cat /proc/meminfo')
        if success:
            for line in mem_info.split('\n'):
                if line.startswith('MemTotal:'):
                    total_mem = int(line.split()[1]) / 1024  # Convert to MB
                    performance['total_memory_mb'] = f"{total_mem:.0f} MB"
                elif line.startswith('MemFree:'):
                    free_mem = int(line.split()[1]) / 1024
                    performance['free_memory_mb'] = f"{free_mem:.0f} MB"
        
        # Current CPU usage
        success, cpu_usage = self.run_adb_command('shell top -n 1 | head -5')
        if success:
            performance['cpu_snapshot'] = cpu_usage
        
        self.test_results['performance'] = performance
        print("✅ Performance metrics test completed")
        return performance
    
    def test_app_functionality(self, package_name: str = "com.android.settings") -> Dict:
        """Test app launch and functionality"""
        print(f"📱 Testing app functionality: {package_name}")
        app_test = {}
        
        # Check if app is installed
        success, output = self.run_adb_command(f'shell pm list packages | grep {package_name}')
        app_test['app_installed'] = success and package_name in output
        
        if app_test['app_installed']:
            # Try to launch the app
            launch_start = time.time()
            success, launch_output = self.run_adb_command(f'shell am start -n {package_name}/.Settings')
            launch_time = time.time() - launch_start
            
            app_test['launch_successful'] = success
            app_test['launch_time_seconds'] = f"{launch_time:.2f}s"
            
            # Wait a moment then check if app is running
            time.sleep(2)
            success, running_apps = self.run_adb_command('shell dumpsys activity activities | grep mCurrentFocus')
            if success:
                app_test['app_currently_running'] = package_name in running_apps
            
            # Close the app
            self.run_adb_command('shell am force-stop com.android.settings')
        
        self.test_results['app_functionality'] = app_test
        print("✅ App functionality test completed")
        return app_test

class ReportGenerator:
    """Generate professional test reports"""
    
    def __init__(self, test_results: Dict):
        self.test_results = test_results
        self.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def generate_console_report(self):
        """Generate a formatted console report"""
        print("\n" + "="*60)
        print("📊 ANDROID DEVICE AUTOMATION TEST REPORT")
        print("="*60)
        print(f"Test completed at: {self.timestamp}")
        print("-"*60)
        
        # Device Info
        if 'device_info' in self.test_results:
            info = self.test_results['device_info']
            print(f"📱 DEVICE: {info.get('brand', 'Unknown')} {info.get('model', 'Unknown')}")
            print(f"🤖 ANDROID: {info.get('android_version', 'Unknown')} (SDK: {info.get('sdk_version', 'Unknown')})")
            print()
        
        # Battery Status
        if 'battery' in self.test_results:
            battery = self.test_results['battery']
            print("🔋 BATTERY STATUS:")
            for key, value in battery.items():
                print(f"   • {key.replace('_', ' ').title()}: {value}")
            print()
        
        # Storage Status
        if 'storage' in self.test_results:
            storage = self.test_results['storage']
            print("💾 STORAGE STATUS:")
            for key, value in storage.items():
                print(f"   • {key.replace('_', ' ').title()}: {value}")
            print()
        
        # Connectivity Status
        if 'connectivity' in self.test_results:
            connectivity = self.test_results['connectivity']
            print("📡 CONNECTIVITY STATUS:")
            for key, value in connectivity.items():
                status = "✅ Active" if value else "❌ Inactive"
                if key == 'current_wifi' and value:
                    status = f"✅ Connected to: {value}"
                print(f"   • {key.replace('_', ' ').title()}: {status}")
            print()
        
        # Performance Metrics
        if 'performance' in self.test_results:
            performance = self.test_results['performance']
            print("⚡ PERFORMANCE METRICS:")
            for key, value in performance.items():
                if key != 'cpu_snapshot':
                    print(f"   • {key.replace('_', ' ').title()}: {value}")
            print()
        
        # Camera Status
        if 'camera' in self.test_results:
            camera = self.test_results['camera']
            print("📸 CAMERA STATUS:")
            for key, value in camera.items():
                if isinstance(value, bool):
                    status = "✅ Working" if value else "❌ Issue detected"
                else:
                    status = str(value)
                print(f"   • {key.replace('_', ' ').title()}: {status}")
            print()
        
        print("="*60)
        print("✅ TEST SUITE COMPLETED SUCCESSFULLY")
        print("="*60)
    
    def save_json_report(self, filename: str = None):
        """Save detailed JSON report"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"android_test_report_{timestamp}.json"
        
        report_data = {
            "test_timestamp": self.timestamp,
            "test_results": self.test_results,
            "summary": {
                "total_tests": len(self.test_results),
                "device_model": self.test_results.get('device_info', {}).get('model', 'Unknown')
            }
        }
        
        try:
            with open(filename, 'w') as f:
                json.dump(report_data, f, indent=2)
            print(f"📄 Detailed JSON report saved: {filename}")
        except Exception as e:
            print(f"❌ Error saving report: {e}")

def main():
    """Main function to run the complete test suite"""
    print("🚀 Android Device Health & Performance Automation Suite")
    print("=" * 60)
    
    # Initialize the tester
    tester = DeviceHealthTester()
    
    # Check ADB connection
    if not tester.check_adb_connection():
        sys.exit(1)
    
    # Select device
    if not tester.select_device():
        sys.exit(1)
    
    print("\n🧪 Starting comprehensive device testing...")
    print("-" * 60)
    
    try:
        # Run all tests
        tester.get_device_info()
        tester.test_battery_health()
        tester.test_storage_health()
        tester.test_connectivity()
        tester.test_camera_functionality()
        tester.test_performance_metrics()
        tester.test_app_functionality()
        
        # Generate reports
        print("\n📊 Generating test reports...")
        report_generator = ReportGenerator(tester.test_results)
        report_generator.generate_console_report()
        report_generator.save_json_report()
        
    except KeyboardInterrupt:
        print("\n⚠️  Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test suite error: {e}")
    
    print("\n🎉 Thanks for using Android Device Automation Suite!")

if __name__ == "__main__":
    main()