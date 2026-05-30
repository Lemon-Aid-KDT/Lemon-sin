import 'package:flutter/material.dart';
import 'package:flutter_web_plugins/url_strategy.dart';

import 'agent_chat_camera_prototype.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  usePathUrlStrategy();

  runApp(
    const MaterialApp(
      debugShowCheckedModeBanner: false,
      initialRoute: '/',
      home: AgentChatCameraPrototype(),
    ),
  );
}
