import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;

class SettingsService {
  static const String _backendUrl = 'http://127.0.0.1:8000/api/v1/settings';

  static File _getLocalConfigFile() {
    final home = Platform.environment['HOME'] ?? '.';
    final dir = Directory('$home/.config/eva_os');
    if (!dir.existsSync()) {
      dir.createSync(recursive: true);
    }
    return File('${dir.path}/settings.json');
  }

  static Map<String, dynamic> loadLocalSettings() {
    try {
      final file = _getLocalConfigFile();
      if (file.existsSync()) {
        final content = file.readAsStringSync();
        if (content.trim().isNotEmpty) {
          return json.decode(content) as Map<String, dynamic>;
        }
      }
    } catch (_) {}
    return {};
  }

  static Future<void> saveLocalSettings(Map<String, dynamic> settings) async {
    try {
      final file = _getLocalConfigFile();
      await file.writeAsString(const JsonEncoder.withIndent('  ').convert(settings));
    } catch (_) {}

    // Synchronize to backend system_config in background if available
    try {
      await http.post(
        Uri.parse(_backendUrl),
        headers: {'Content-Type': 'application/json'},
        body: json.encode(settings),
      ).timeout(const Duration(milliseconds: 1500));
    } catch (_) {}
  }

  static Future<Map<String, dynamic>> fetchBackendSettings() async {
    try {
      final res = await http.get(Uri.parse(_backendUrl)).timeout(const Duration(milliseconds: 1500));
      if (res.statusCode == 200) {
        return json.decode(res.body) as Map<String, dynamic>;
      }
    } catch (_) {}
    return {};
  }
}
