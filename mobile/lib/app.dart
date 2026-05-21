import 'package:flutter/material.dart';

import 'app_controller.dart';
import 'features/consent/consent_gate_screen.dart';
import 'features/dashboard/dashboard_screen.dart';
import 'features/supplements/supplement_flow_screen.dart';
import 'features/supplements/supplement_repository.dart';
import 'shared/widgets/error_panel.dart';

/// Lemon Aid mobile application.
class LemonAidApp extends StatelessWidget {
  /// Creates the app.
  ///
  /// Args:
  ///   repository: Backend or fake repository implementation.
  const LemonAidApp({required this.repository, super.key});

  /// Repository used by the app controller.
  final LemonAidRepository repository;

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Lemon Aid',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xFF4E8F73)),
        useMaterial3: true,
      ),
      home: LemonAidHome(repository: repository),
    );
  }
}

/// Root mobile screen with the minimum P2 tabs.
class LemonAidHome extends StatefulWidget {
  /// Creates the root mobile screen.
  const LemonAidHome({required this.repository, super.key});

  /// Repository used by the app controller.
  final LemonAidRepository repository;

  @override
  State<LemonAidHome> createState() => _LemonAidHomeState();
}

class _LemonAidHomeState extends State<LemonAidHome> {
  late final AppController _controller;
  int _selectedIndex = 0;

  @override
  void initState() {
    super.initState();
    _controller = AppController(repository: widget.repository);
    _controller.bootstrap();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _controller,
      builder: (BuildContext context, Widget? child) {
        final List<Widget> tabs = <Widget>[
          DashboardScreen(controller: _controller),
          SupplementFlowScreen(
            controller: _controller,
            onClose: () {
              setState(() {
                _selectedIndex = 0;
              });
            },
          ),
          ConsentGateScreen(controller: _controller),
        ];
        final bool immersiveSupplement = _selectedIndex == 1;

        return Scaffold(
          appBar: immersiveSupplement
              ? null
              : AppBar(
                  title: const Text('Lemon Aid'),
                  actions: <Widget>[
                    IconButton(
                      tooltip: 'Refresh dashboard',
                      onPressed: _controller.busy
                          ? null
                          : () {
                              _controller.refreshDashboard();
                            },
                      icon: const Icon(Icons.refresh),
                    ),
                  ],
                ),
          body: Column(
            children: <Widget>[
              if (_controller.busy) const LinearProgressIndicator(),
              if (_controller.apiError != null)
                ErrorPanel(
                  error: _controller.apiError!,
                  onDismissed: _controller.clearMessages,
                ),
              if (_controller.notice != null)
                _NoticePanel(
                  message: _controller.notice!,
                  onDismissed: _controller.clearMessages,
                ),
              Expanded(child: tabs[_selectedIndex]),
            ],
          ),
          bottomNavigationBar: immersiveSupplement
              ? null
              : NavigationBar(
                  selectedIndex: _selectedIndex,
                  onDestinationSelected: (int index) {
                    setState(() {
                      _selectedIndex = index;
                    });
                  },
                  destinations: const <NavigationDestination>[
                    NavigationDestination(
                      icon: Icon(Icons.dashboard_outlined),
                      selectedIcon: Icon(Icons.dashboard),
                      label: 'Dashboard',
                    ),
                    NavigationDestination(
                      icon: Icon(Icons.add_a_photo_outlined),
                      selectedIcon: Icon(Icons.add_a_photo),
                      label: 'Supplement',
                    ),
                    NavigationDestination(
                      icon: Icon(Icons.verified_user_outlined),
                      selectedIcon: Icon(Icons.verified_user),
                      label: 'Consents',
                    ),
                  ],
                ),
        );
      },
    );
  }
}

class _NoticePanel extends StatelessWidget {
  const _NoticePanel({required this.message, required this.onDismissed});

  final String message;
  final VoidCallback onDismissed;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Theme.of(context).colorScheme.secondaryContainer,
      child: ListTile(
        leading: const Icon(Icons.check_circle_outline),
        title: Text(message),
        trailing: IconButton(
          tooltip: 'Dismiss',
          onPressed: onDismissed,
          icon: const Icon(Icons.close),
        ),
      ),
    );
  }
}
