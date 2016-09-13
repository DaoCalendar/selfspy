# Copyright 2012 Bjarte Johansen

# This file is part of Selfspy

# Selfspy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# Selfspy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with Selfspy.  If not, see <http://www.gnu.org/licenses/>.

from Foundation import NSObject
from AppKit import NSApplication, NSApp, NSWorkspace
from Cocoa import (
    NSEvent, NSFlagsChanged,
    NSKeyDown, NSKeyUp, NSKeyDownMask, NSKeyUpMask,
    NSLeftMouseDown, NSLeftMouseUpMask, NSLeftMouseDownMask,
    NSRightMouseDown, NSRightMouseUpMask, NSRightMouseDownMask,
    NSMouseMoved, NSMouseMovedMask,
    NSScrollWheel, NSScrollWheelMask,
    NSFlagsChangedMask,
    NSAlternateKeyMask, NSCommandKeyMask, NSControlKeyMask,
    NSShiftKeyMask, NSAlphaShiftKeyMask,
    NSApplicationActivationPolicyProhibited,
    NSWorkspaceDidWakeNotification, NSWorkspaceWillSleepNotification,
    NSWorkspaceWillPowerOffNotification
)
from Quartz import (
    CGWindowListCopyWindowInfo,
    kCGWindowListExcludeDesktopElements,
    kCGWindowListOptionOnScreenOnly,
    kCGNullWindowID
)
from PyObjCTools import AppHelper
import config as cfg
import signal
import time

FORCE_SCREEN_CHANGE = 10
WAIT_ANIMATION = 1

class Sniffer:
    def __init__(self):
        self.key_hook = lambda x: True
        self.mouse_button_hook = lambda x: True
        self.mouse_move_hook = lambda x: True
        self.screen_hook = lambda x: True
        self.last_check_windows = time.time()

    def createAppDelegate(self):
        sc = self

        class AppDelegate(NSObject):

            SLEEP = u'Sleep'
            POWER_OFF = u'Power Off'
            NONE = u'\0'

            DUMMY_SCREEN_EVENT = [u'System', NONE, 0, 0, 0, 0]
            DUMMY_KEY_EVENT = [0, [], u'\0', False]

            def applicationDidFinishLaunching_(self, notification):
                mask = (NSKeyDownMask
                        | NSKeyUpMask
                        | NSLeftMouseDownMask
                        | NSLeftMouseUpMask
                        | NSRightMouseDownMask
                        | NSRightMouseUpMask
                        | NSMouseMovedMask
                        | NSScrollWheelMask
                        | NSFlagsChangedMask)
                NSEvent.addGlobalMonitorForEventsMatchingMask_handler_(mask, sc.handler)

                # use reference to outer class (Sniffer)'s attributes
                self.screen_hook = sc.screen_hook
                self.key_hook = sc.key_hook

                self.registerNotifications()

            def registerNotifications(self):
                """Register the app to listen to system state events such as:
                wake, sleep, and power off
                """
                workspace = NSWorkspace.sharedWorkspace()
                notificationCenter = workspace.notificationCenter()
                notificationCenter.addObserver_selector_name_object_(
                    self,
                    self.receiveSleepNotification_,
                    NSWorkspaceWillSleepNotification,
                    None
                )
                notificationCenter.addObserver_selector_name_object_(
                    self,
                    self.receiveWakeNotification_,
                    NSWorkspaceDidWakeNotification,
                    None
                )
                notificationCenter.addObserver_selector_name_object_(
                    self,
                    self.receivePowerOffNotification_,
                    NSWorkspaceWillPowerOffNotification,
                    None
                )

            def generateSystemEvent(self, state):
                """Generate an system event and input a dummy key to ensure the
                event is logged

                :state: unicode string of the System's state

                """
                if not isinstance(state, unicode):
                    raise TypeError('Expected {} but received {}'
                            .format('unicode', type(state)))

                screen_event = self.DUMMY_SCREEN_EVENT
                screen_event[1] = state

                self.screen_hook(*screen_event)
                self.key_hook(*self.DUMMY_KEY_EVENT)

            def receiveSleepNotification_(self, notification):
                self.generateSystemEvent(self.SLEEP)

            def receiveWakeNotification_(self, notification):
                """ This maybe useful in the future
                """
                pass

            def receivePowerOffNotification_(self, notification):
                self.generateSystemEvent(self.POWER_OFF)

            def applicationWillResignActive(self, notification):
                self.applicationWillTerminate_(notification)
                return True

            def applicationShouldTerminate_(self, notification):
                self.applicationWillTerminate_(notification)
                return True

            def applicationWillTerminate_(self, notification):
                # need to release the lock here as when the
                # application terminates it does not run the rest the
                # original main, only the code that has crossed the
                # pyobc bridge.
                if cfg.LOCK.is_locked():
                    cfg.LOCK.release()
                print("Releasing lock and exiting")
                return None

        return AppDelegate

    def run(self):
        NSApplication.sharedApplication()
        delegate = self.createAppDelegate().alloc().init()
        NSApp().setDelegate_(delegate)
        NSApp().setActivationPolicy_(NSApplicationActivationPolicyProhibited)
        self.workspace = NSWorkspace.sharedWorkspace()

        def handler(signal, frame):
            AppHelper.stopEventLoop()
        signal.signal(signal.SIGINT, handler)
        signal.signal(signal.SIGTERM, handler)
        AppHelper.runEventLoop()

    def cancel(self):
        AppHelper.stopEventLoop()

    def handler(self, event):
        try:
            check_windows = False
            event_type = event.type()
            todo = lambda: None
            if (
                time.time() - self.last_check_windows > FORCE_SCREEN_CHANGE and
                event_type != NSKeyUp
            ):
                self.last_check_windows = time.time()
                check_windows = True
            loc = NSEvent.mouseLocation()
            if event_type == NSLeftMouseDown:
                check_windows = True
                todo = lambda: self.mouse_button_hook(1, loc.x, loc.y)
            elif event_type == NSRightMouseDown:
                check_windows = True
                todo = lambda: self.mouse_button_hook(3, loc.x, loc.y)
            elif event_type == NSScrollWheel:
                if event.deltaY() > 0:
                    todo = lambda: self.mouse_button_hook(4, loc.x, loc.y)
                elif event.deltaY() < 0:
                    todo = lambda: self.mouse_button_hook(5, loc.x, loc.y)
                if event.deltaX() > 0:
                    todo = lambda: self.mouse_button_hook(6, loc.x, loc.y)
                elif event.deltaX() < 0:
                    todo = lambda: self.mouse_button_hook(7, loc.x, loc.y)
            elif event_type == NSKeyDown:
                flags = event.modifierFlags()
                modifiers = []  # OS X api doesn't care it if is left or right
                if flags & NSControlKeyMask:
                    modifiers.append('Ctrl')
                if flags & NSAlternateKeyMask:
                    modifiers.append('Alt')
                if flags & NSCommandKeyMask:
                    modifiers.append('Cmd')
                if flags & (NSShiftKeyMask | NSAlphaShiftKeyMask):
                    modifiers.append('Shift')
                character = event.charactersIgnoringModifiers()
                # these two get a special case because I am unsure of
                # their unicode value
                if event.keyCode() == 36:
                    character = "Enter"
                elif event.keyCode() == 51:
                    character = "Backspace"
                todo = lambda: self.key_hook(event.keyCode(),
                              modifiers,
                              keycodes.get(character,
                                           character),
                              event.isARepeat())
            elif event_type == NSMouseMoved:
                todo = lambda: self.mouse_move_hook(loc.x, loc.y)
            elif event_type == NSFlagsChanged:
                # Register leaving this window after animations are done
                # approx (1 second)
                self.last_check_windows = (time.time() - FORCE_SCREEN_CHANGE +
                                           WAIT_ANIMATION)
                check_windows = True
            if check_windows:
                activeApps = self.workspace.runningApplications()
                for app in activeApps:
                    if app.isActive():
                        app_name = app.localizedName()
                        options = kCGWindowListOptionOnScreenOnly | kCGWindowListExcludeDesktopElements
                        windowList = CGWindowListCopyWindowInfo(options,
                                                                kCGNullWindowID)
                        windowListLowPrio = [
                            w for w in windowList
                            if w['kCGWindowLayer'] or not w.get('kCGWindowName', u'')
                        ]
                        windowList = [
                            w for w in windowList
                            if not w['kCGWindowLayer'] and w.get('kCGWindowName', u'')
                        ]
                        windowList = windowList + windowListLowPrio
                        for window in windowList:
                            if window['kCGWindowOwnerName'] == app_name:
                                geometry = window['kCGWindowBounds']
                                self.screen_hook(window['kCGWindowOwnerName'],
                                                 window.get('kCGWindowName', u''),
                                                 geometry['X'],
                                                 geometry['Y'],
                                                 geometry['Width'],
                                                 geometry['Height'])
                                break
                        break
            todo()
        except (SystemExit, KeyboardInterrupt):
            AppHelper.stopEventLoop()
            return
        except:
            AppHelper.stopEventLoop()
            raise

# Cocoa does not provide a good api to get the keycodes, therefore we
# have to provide our own.
keycodes = {
    u"\u0009": "Tab",
    u"\u001b": "Escape",
    u"\uf700": "Up",
    u"\uF701": "Down",
    u"\uF702": "Left",
    u"\uF703": "Right",
    u"\uF704": "F1",
    u"\uF705": "F2",
    u"\uF706": "F3",
    u"\uF707": "F4",
    u"\uF708": "F5",
    u"\uF709": "F6",
    u"\uF70A": "F7",
    u"\uF70B": "F8",
    u"\uF70C": "F9",
    u"\uF70D": "F10",
    u"\uF70E": "F11",
    u"\uF70F": "F12",
    u"\uF710": "F13",
    u"\uF711": "F14",
    u"\uF712": "F15",
    u"\uF713": "F16",
    u"\uF714": "F17",
    u"\uF715": "F18",
    u"\uF716": "F19",
    u"\uF717": "F20",
    u"\uF718": "F21",
    u"\uF719": "F22",
    u"\uF71A": "F23",
    u"\uF71B": "F24",
    u"\uF71C": "F25",
    u"\uF71D": "F26",
    u"\uF71E": "F27",
    u"\uF71F": "F28",
    u"\uF720": "F29",
    u"\uF721": "F30",
    u"\uF722": "F31",
    u"\uF723": "F32",
    u"\uF724": "F33",
    u"\uF725": "F34",
    u"\uF726": "F35",
    u"\uF727": "Insert",
    u"\uF728": "Delete",
    u"\uF729": "Home",
    u"\uF72A": "Begin",
    u"\uF72B": "End",
    u"\uF72C": "PageUp",
    u"\uF72D": "PageDown",
    u"\uF72E": "PrintScreen",
    u"\uF72F": "ScrollLock",
    u"\uF730": "Pause",
    u"\uF731": "SysReq",
    u"\uF732": "Break",
    u"\uF733": "Reset",
    u"\uF734": "Stop",
    u"\uF735": "Menu",
    u"\uF736": "User",
    u"\uF737": "System",
    u"\uF738": "Print",
    u"\uF739": "ClearLine",
    u"\uF73A": "ClearDisplay",
    u"\uF73B": "InsertLine",
    u"\uF73C": "DeleteLine",
    u"\uF73D": "InsertChar",
    u"\uF73E": "DeleteChar",
    u"\uF73F": "Prev",
    u"\uF740": "Next",
    u"\uF741": "Select",
    u"\uF742": "Execute",
    u"\uF743": "Undo",
    u"\uF744": "Redo",
    u"\uF745": "Find",
    u"\uF746": "Help",
    u"\uF747": "ModeSwitch"
}
