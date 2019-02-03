import ui
import re
import dialogs
import socket
from objc_util import *
from enum import Enum, auto


NSUserDefaults = ObjCClass('NSUserDefaults')

class H190RemoteController:
	_COMMANDS = {
		"power": b"p",
		"source_input": b"i",
		"volume_control": b"v",
		"volume_mute": b"m"
	}

	INPUTS = {
		1: "Balanced",
		2: "Analog 1",
		3: "Analog 2",
		4: "Coaxial",
		5: "Optical 1",
		6: "Optical 2",
		7: "Optical 3",
		8: "USB",
		9: "Network"
	}

	class VolumeChange(Enum):
		UP = auto()
		DOWN = auto()

	class SwitchState(Enum):
		ON = auto()
		OFF = auto()

	def __init__(self):
		socket.setdefaulttimeout(2.0)
		self._host = None
		self._port = 50001

	def _exchange_data(self, command, parameter):
		if not self._host:
			return
		with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
			s.connect((self._host, self._port))
			s.sendall(b"-%s.%s\r" % (command, parameter))
			reply = s.recv(64)
			current = re.match(b'-%s\\.([0-9]+)' % command, reply)
			return current[1]

	def _status_request(self, command):
		return self._exchange_data(command, b'?').decode('utf-8')

	def _send_command(self, command, parameter):
		return self._exchange_data(command, parameter).decode('utf-8')

	def current_input(self):
		return int(self._status_request(self._COMMANDS["source_input"]))

	def current_volume(self):
		return int(self._status_request(self._COMMANDS["volume_control"]))

	def power_state(self):
		state = self._status_request(self._COMMANDS["power"])
		return self.SwitchState.ON if state == '1' else self.SwitchState.OFF

	def mute_state(self):
		state = self._status_request(self._COMMANDS["volume_mute"])
		return self.SwitchState.ON if state == '1' else self.SwitchState.OFF

	def mute(self, state):
		state_string = b'1' if state is self.SwitchState.ON else b'0'
		return self._send_command(self._COMMANDS["volume_mute"], state_string)

	def change_volume(self, direction):
		direction_string = b'u' if direction is self.VolumeChange.UP else b'd'
		return self._send_command(self._COMMANDS["volume_control"], direction_string)

	def set_volume(self, volume):
		volume_string = str(volume).encode()
		return self._send_command(self._COMMANDS["volume_control"], volume_string)

	def change_input(self, input_number):
		input_number_string = str(input_number).encode()
		return self._send_command(self._COMMANDS['source_input'], input_number_string)

	def set_power(self, state):
		state_string = b'1' if state is self.SwitchState.ON else b'0'
		return self._send_command(self._COMMANDS['power'], state_string)

	def set_host(self, host):
		self._host = host

	def host(self):
		return self._host

	def is_reachable(self, host):
		try:
			_ = socket.create_connection((host, self._port), timeout=0.5)
		except:
			return False
		else:
			return True

class ViewController:
	def __init__(self, remote_controller):
		view_bindings = {
			'mute_action': self._mute_action,
			'change_volume_action': self._change_volume_action,
			'set_volume_action': self._set_volume_action,
			'power_action': self._power_action,
			'address_changed': self._address_changed,
		}
		self.view = ui.load_view(bindings=view_bindings)
		self.remote_controller = remote_controller
		self._defaults = NSUserDefaults.standardUserDefaults()
		
		self._setup_view()

	def _setup_view(self):
		for i, v in enumerate(self.view['inputs'].subviews, start=1):
			v.action = self._input_select_action
			v.input_number = i
			v.title = H190RemoteController.INPUTS[i]
		self.view['address'].clear_button_mode = 'always'
		self.view['address'].autocapitalization_type = ui.AUTOCAPITALIZE_NONE
		self.view['address'].keyboard_type = ui.KEYBOARD_URL
		host = str(self._defaults.stringForKey_('host'))
		if not host:
			return
		if not self.remote_controller.is_reachable(host):
			return
		self.view['address'].text = host
		self.remote_controller.set_host(host)
		self.view.flex = 'WH'
		self.view["current_input"].text = H190RemoteController.INPUTS[self.remote_controller.current_input()]
		self.view["current_volume"].text = str(self.remote_controller.current_volume())
		self.view["power"].value = (self.remote_controller.power_state() is H190RemoteController.SwitchState.ON)
		self.view["mute"].value = (self.remote_controller.mute_state() is H190RemoteController.SwitchState.ON)


	def _address_changed(self, sender):
		host = sender.text
		if self.remote_controller.is_reachable(host):
			self.remote_controller.set_host(host)
			self._defaults.setObject_forKey_(host, 'host')
		else:
			dialogs.hud_alert(f'{host} not reachable', icon='error')

	def _input_select_action(self, sender):
		new_input = self.remote_controller.change_input(sender.input_number)
		self.view['current_input'].text = H190RemoteController.INPUTS[int(new_input)]

	def _change_volume_action(self, sender):
		direction = H190RemoteController.VolumeChange.UP if sender.name == 'volume_up' else H190RemoteController.VolumeChange.DOWN
		new_volume = self.remote_controller.change_volume(direction)
		self.view["current_volume"].text = new_volume

	def _set_volume_action(self, sender):
		new_volume = self.remote_controller.set_volume(sender.new_volume)
		self.view["current_volume"].text = new_volume

	def _mute_action(self, sender):
		new_state = H190RemoteController.SwitchState.ON if sender.value else H190RemoteController.SwitchState.OFF
		self.remote_controller.mute(new_state)

	def _power_action(self, sender):
		new_state = H190RemoteController.SwitchState.ON if sender.value else H190RemoteController.SwitchState.OFF
		self.remote_controller.set_power(new_state)

	def present_view(self, style='default'):
		self.view.present(style)


if __name__ == '__main__':
	try:
		h190_remote = H190RemoteController()
		ViewController(h190_remote).present_view('fullscreen')
	except Exception as e:
		dialogs.alert('Error', message=str(e))
