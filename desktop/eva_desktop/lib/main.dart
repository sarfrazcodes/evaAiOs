import 'package:flutter/material.dart';
import 'core/theme/theme_notifier.dart';
import 'core/widgets/desktop_shell.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const EvaOSApp());
}

class EvaOSApp extends StatefulWidget {
  final ThemeNotifier? themeNotifier;
  const EvaOSApp({super.key, this.themeNotifier});

  @override
  State<EvaOSApp> createState() => _EvaOSAppState();
}

class _EvaOSAppState extends State<EvaOSApp> {
  late final ThemeNotifier _themeNotifier;

  @override
  void initState() {
    super.initState();
    _themeNotifier = widget.themeNotifier ?? ThemeNotifier();
  }

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: _themeNotifier,
      builder: (context, _) {
        final themeData = _themeNotifier.getThemeData(context);
        return MaterialApp(
          title: 'EVA AI OS',
          debugShowCheckedModeBanner: false,
          themeMode: _themeNotifier.themeMode,
          theme: themeData,
          darkTheme: themeData,
          home: DesktopShell(themeNotifier: _themeNotifier),
        );
      },
    );
  }
}
