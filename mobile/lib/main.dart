// main.dart — Lemon Aid 앱 진입점

import 'package:flutter/material.dart';
import 'package:flutter_web_plugins/url_strategy.dart';

import 'app_launcher.dart' deferred as app_launcher;
import 'prototypes/agent_chat_camera_prototype.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final initialRoute =
      WidgetsBinding.instance.platformDispatcher.defaultRouteName;
  final initialPath = Uri.base.path;

  if (initialRoute.startsWith('/prototype/agent-chat') ||
      initialPath.startsWith('/prototype/agent-chat')) {
    runApp(
      const MaterialApp(
        debugShowCheckedModeBanner: false,
        initialRoute: '/',
        home: AgentChatCameraPrototype(),
      ),
    );
    return;
  }

  usePathUrlStrategy();

  await app_launcher.loadLibrary();
  await app_launcher.runLemonAidApp();
}
