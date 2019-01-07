import ui
import dialogs
import telnetlib
from enum import Enum, auto

HOST = "192.168.123.12"
PORT = 50001

class H190RemoteController:
	__COMMANDS = {
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

	def __init__(self, telnet_connection):
		self.__telnet_connection = telnet_connection

	def __status_request(self, command):
		self.__telnet_connection.write(b"-%s.?\r" % command)
		_, match, _ = self.__telnet_connection.expect([b"-%s\.([0-9]+)" % command])
		return match[1].decode("utf-8")

	def __send_command(self, command, parameter):
		self.__telnet_connection.write(b"-%s.%s\r" % (command, parameter))
		_, match, _ = self.__telnet_connection.expect([b"-%s\.([0-9]+)" % command])
		return match[1].decode("utf-8")

	def current_input(self):
		return int(self.__status_request(self.__COMMANDS["source_input"]))

	def current_volume(self):
		return int(self.__status_request(self.__COMMANDS["volume_control"]))

	def power_state(self):
		state = self.__status_request(self.__COMMANDS["power"])
		return self.SwitchState.ON if state == '1' else self.SwitchState.OFF

	def mute_state(self):
		state = self.__status_request(self.__COMMANDS["volume_mute"])
		return self.SwitchState.ON if state == '1' else self.SwitchState.OFF

	def mute(self, state):
		state_string = b'1' if state is self.SwitchState.ON else b'0'
		return self.__send_command(self.__COMMANDS["volume_mute"], state_string)

	def change_volume(self, direction):
		direction_string = b'u' if direction is self.VolumeChange.UP else b'd'
		return self.__send_command(self.__COMMANDS["volume_control"], direction_string)

	def set_volume(self, volume):
		volume_string = str(volume).encode()
		return self.__send_command(self.__COMMANDS["volume_control"], volume_string)

	def change_input(self, input_number):
		input_number_string = str(input_number).encode()
		return self.__send_command(self.__COMMANDS['source_input'], input_number_string)

	def set_power(self, state):
		state_string = b'1' if state is self.SwitchState.ON else b'0'
		return self.__send_command(self.__COMMANDS['power'], state_string)


class ViewController:
	def __init__(self, remote_controller):
		view_bindings = {
			'mute_action': self.__mute_action,
			'change_volume_action': self.__change_volume_action,
			'set_volume_action': self.__set_volume_action,
			'power_action': self.__power_action
		}
		self.view = ui.load_view(bindings=view_bindings)
		self.remote_controller = remote_controller

		self.__setup_view()

	def __setup_view(self):
		self.view.flex = 'WH'
		self.view["current_input"].text = H190RemoteController.INPUTS[self.remote_controller.current_input()]
		self.view["current_volume"].text = str(self.remote_controller.current_volume())
		self.view["power"].value = (self.remote_controller.power_state() is H190RemoteController.SwitchState.ON)
		self.view["mute"].value = (self.remote_controller.mute_state() is H190RemoteController.SwitchState.ON)
		for i, v in enumerate(self.view['inputs'].subviews, start=1):
			v.action = self.__input_select_action
			v.input_number = i
			v.title = H190RemoteController.INPUTS[i]

	def __input_select_action(self, sender):
		new_input = self.remote_controller.change_input(sender.input_number)
		self.view['current_input'].text = H190RemoteController.INPUTS[int(new_input)]

	def __change_volume_action(self, sender):
		direction = H190RemoteController.VolumeChange.UP if sender.name == 'volume_up' else H190RemoteController.VolumeChange.DOWN
		new_volume = self.remote_controller.change_volume(direction)
		self.view["current_volume"].text = new_volume

	def __set_volume_action(self, sender):
		new_volume = self.remote_controller.set_volume(sender.new_volume)
		self.view["current_volume"].text = new_volume

	def __mute_action(self, sender):
		new_state = H190RemoteController.SwitchState.ON if sender.value else H190RemoteController.SwitchState.OFF
		self.remote_controller.mute(new_state)

	def __power_action(self, sender):
		new_state = H190RemoteController.SwitchState.ON if sender.value else H190RemoteController.SwitchState.OFF
		self.remote_controller.set_power(new_state)

	def present_view(self, style='default'):
		self.view.present(style)


if __name__ == '__main__':
	try:
		tn = telnetlib.Telnet(HOST, PORT, timeout=5)
		h190_remote = H190RemoteController(tn)
		ViewController(h190_remote).present_view('fullscreen')
	except Exception as e:
		dialogs.alert('Error', message=str(e))
