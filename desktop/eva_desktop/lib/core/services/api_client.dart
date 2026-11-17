import 'dart:async';
import 'dart:convert';
import 'package:http/http.dart' as http;

class EvaApiClient {
  static const String baseUrl = 'http://127.0.0.1:8000';

  // ── Health & System Info ──────────────────────────────────────────────────

  static Future<Map<String, dynamic>?> getSystemInfo() async {
    try {
      final res = await http.get(Uri.parse('$baseUrl/api/system/info')).timeout(const Duration(seconds: 3));
      if (res.statusCode == 200) {
        return json.decode(res.body) as Map<String, dynamic>;
      }
    } catch (_) {}
    return null;
  }

  static Future<Map<String, dynamic>?> getDetailedHealth() async {
    try {
      final res = await http.get(Uri.parse('$baseUrl/api/health/detailed')).timeout(const Duration(seconds: 3));
      if (res.statusCode == 200) {
        return json.decode(res.body) as Map<String, dynamic>;
      }
    } catch (_) {}
    return null;
  }

  static Future<bool> isBackendHealthy() async {
    try {
      final res = await http.get(Uri.parse('$baseUrl/api/health')).timeout(const Duration(milliseconds: 1500));
      return res.statusCode == 200;
    } catch (_) {
      return false;
    }
  }

  // ── TTS & Audio ───────────────────────────────────────────────────────────

  static Future<Map<String, dynamic>?> getTtsStatus() async {
    try {
      final res = await http.get(Uri.parse('$baseUrl/api/v1/tts/status')).timeout(const Duration(milliseconds: 1500));
      if (res.statusCode == 200) {
        return json.decode(res.body) as Map<String, dynamic>;
      }
    } catch (_) {}
    return null;
  }

  static Future<bool> stopTts() async {
    try {
      final res = await http.post(Uri.parse('$baseUrl/api/v1/tts/stop')).timeout(const Duration(seconds: 2));
      return res.statusCode == 200;
    } catch (_) {
      return false;
    }
  }

  // ── Conversations ─────────────────────────────────────────────────────────

  static Future<List<Map<String, dynamic>>> getConversations() async {
    try {
      final res = await http.get(Uri.parse('$baseUrl/api/v1/conversations')).timeout(const Duration(seconds: 4));
      if (res.statusCode == 200) {
        return (json.decode(res.body) as List).cast<Map<String, dynamic>>();
      }
    } catch (_) {}
    return [];
  }

  static Future<List<Map<String, dynamic>>> getConversationMessages(String convId) async {
    try {
      final res = await http.get(Uri.parse('$baseUrl/api/v1/conversations/$convId/messages')).timeout(const Duration(seconds: 4));
      if (res.statusCode == 200) {
        return (json.decode(res.body) as List).cast<Map<String, dynamic>>();
      }
    } catch (_) {}
    return [];
  }

  static Future<bool> deleteConversation(String convId) async {
    try {
      final res = await http.delete(Uri.parse('$baseUrl/api/v1/conversations/$convId')).timeout(const Duration(seconds: 3));
      return res.statusCode == 200;
    } catch (_) {
      return false;
    }
  }

  // ── Task Manager ──────────────────────────────────────────────────────────

  static Future<List<Map<String, dynamic>>> getTasks({int limit = 100}) async {
    try {
      final res = await http.get(Uri.parse('$baseUrl/api/v1/core/tasks?limit=$limit')).timeout(const Duration(seconds: 4));
      if (res.statusCode == 200) {
        return (json.decode(res.body) as List).cast<Map<String, dynamic>>();
      }
    } catch (_) {}
    return [];
  }

  static Future<Map<String, dynamic>?> getTask(String taskId) async {
    try {
      final res = await http.get(Uri.parse('$baseUrl/api/v1/core/task/$taskId')).timeout(const Duration(seconds: 3));
      if (res.statusCode == 200) {
        return json.decode(res.body) as Map<String, dynamic>;
      }
    } catch (_) {}
    return null;
  }

  static Future<Map<String, dynamic>?> executeTask(String taskId) async {
    try {
      final res = await http.post(Uri.parse('$baseUrl/api/v1/core/task/$taskId/execute')).timeout(const Duration(seconds: 5));
      if (res.statusCode == 200) {
        return json.decode(res.body) as Map<String, dynamic>;
      }
    } catch (_) {}
    return null;
  }

  static Future<Map<String, dynamic>?> controlTask(String taskId, String action) async {
    try {
      final res = await http.post(Uri.parse('$baseUrl/api/v1/core/task/$taskId/$action')).timeout(const Duration(seconds: 3));
      if (res.statusCode == 200) {
        return json.decode(res.body) as Map<String, dynamic>;
      }
    } catch (_) {}
    return null;
  }

  static Future<Map<String, dynamic>?> respondConfirmation(String confirmationId, bool approve) async {
    try {
      final action = approve ? 'approve' : 'deny';
      final res = await http.post(Uri.parse('$baseUrl/api/v1/core/confirmation/$confirmationId/$action')).timeout(const Duration(seconds: 4));
      if (res.statusCode == 200) {
        return json.decode(res.body) as Map<String, dynamic>;
      }
    } catch (_) {}
    return null;
  }

  // ── Application Manager ───────────────────────────────────────────────────

  static Future<List<Map<String, dynamic>>> getApplications() async {
    try {
      final res = await http.get(Uri.parse('$baseUrl/api/v1/apps')).timeout(const Duration(seconds: 4));
      if (res.statusCode == 200) {
        return (json.decode(res.body) as List).cast<Map<String, dynamic>>();
      }
    } catch (_) {}
    return [];
  }

  static Future<Map<String, dynamic>?> performAppAction(String application, String action) async {
    try {
      final res = await http.post(
        Uri.parse('$baseUrl/api/v1/apps/action'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({'application': application, 'action': action}),
      ).timeout(const Duration(seconds: 5));
      if (res.statusCode == 200) {
        return json.decode(res.body) as Map<String, dynamic>;
      }
    } catch (_) {}
    return null;
  }

  // ── Safe File Explorer ────────────────────────────────────────────────────

  static Future<Map<String, dynamic>?> listFiles(String path) async {
    try {
      final encoded = Uri.encodeQueryComponent(path);
      final res = await http.get(Uri.parse('$baseUrl/api/v1/files/list?path=$encoded')).timeout(const Duration(seconds: 4));
      if (res.statusCode == 200) {
        return json.decode(res.body) as Map<String, dynamic>;
      }
    } catch (_) {}
    return null;
  }

  static Future<Map<String, dynamic>?> readFile(String path) async {
    try {
      final encoded = Uri.encodeQueryComponent(path);
      final res = await http.get(Uri.parse('$baseUrl/api/v1/files/read?path=$encoded')).timeout(const Duration(seconds: 5));
      if (res.statusCode == 200) {
        return json.decode(res.body) as Map<String, dynamic>;
      }
    } catch (_) {}
    return null;
  }

  static Future<bool> createFile(String path, String content, {bool isDirectory = false}) async {
    try {
      final res = await http.post(
        Uri.parse('$baseUrl/api/v1/files/create'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({
          'path': path,
          'content': content,
          'is_directory': isDirectory,
        }),
      ).timeout(const Duration(seconds: 4));
      return res.statusCode == 200;
    } catch (_) {
      return false;
    }
  }

  // ── Memory Explorer ───────────────────────────────────────────────────────

  static Future<List<Map<String, dynamic>>> getMemories({
    String? category,
    String? privacy,
    String? search,
    bool? pinned,
  }) async {
    try {
      final params = <String, String>{};
      if (category != null && category.isNotEmpty) params['category'] = category;
      if (privacy != null && privacy.isNotEmpty) params['privacy'] = privacy;
      if (search != null && search.isNotEmpty) params['search'] = search;
      if (pinned != null) params['pinned'] = pinned.toString();

      final uri = Uri.parse('$baseUrl/api/v1/memories').replace(queryParameters: params.isNotEmpty ? params : null);
      final res = await http.get(uri).timeout(const Duration(seconds: 4));
      if (res.statusCode == 200) {
        return (json.decode(res.body) as List).cast<Map<String, dynamic>>();
      }
    } catch (_) {}
    return [];
  }

  static Future<Map<String, dynamic>?> createMemory({
    required String title,
    required String content,
    String category = 'General',
    String privacy = 'public',
    bool pinned = false,
  }) async {
    try {
      final res = await http.post(
        Uri.parse('$baseUrl/api/v1/memories'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({
          'title': title,
          'content': content,
          'category': category,
          'privacy': privacy,
          'pinned': pinned,
          'source': 'user',
        }),
      ).timeout(const Duration(seconds: 4));
      if (res.statusCode == 200) {
        return json.decode(res.body) as Map<String, dynamic>;
      }
    } catch (_) {}
    return null;
  }

  static Future<Map<String, dynamic>?> updateMemory(
    String memoryId, {
    String? title,
    String? content,
    String? category,
    String? privacy,
    bool? pinned,
  }) async {
    try {
      final body = <String, dynamic>{};
      if (title != null) body['title'] = title;
      if (content != null) body['content'] = content;
      if (category != null) body['category'] = category;
      if (privacy != null) body['privacy'] = privacy;
      if (pinned != null) body['pinned'] = pinned;

      final res = await http.put(
        Uri.parse('$baseUrl/api/v1/memories/$memoryId'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode(body),
      ).timeout(const Duration(seconds: 4));
      if (res.statusCode == 200) {
        return json.decode(res.body) as Map<String, dynamic>;
      }
    } catch (_) {}
    return null;
  }

  static Future<bool> deleteMemory(String memoryId) async {
    try {
      final res = await http.delete(Uri.parse('$baseUrl/api/v1/memories/$memoryId')).timeout(const Duration(seconds: 3));
      return res.statusCode == 200;
    } catch (_) {
      return false;
    }
  }

  static Future<bool> togglePinMemory(String memoryId) async {
    try {
      final res = await http.post(Uri.parse('$baseUrl/api/v1/memories/$memoryId/pin')).timeout(const Duration(seconds: 3));
      return res.statusCode == 200;
    } catch (_) {
      return false;
    }
  }

  // ── Owner Profile & Verified Identity ─────────────────────────────────────

  static Future<Map<String, dynamic>?> getOwnerProfile() async {
    try {
      final res = await http.get(Uri.parse('$baseUrl/api/v1/memories/profile')).timeout(const Duration(seconds: 4));
      if (res.statusCode == 200) {
        return json.decode(res.body) as Map<String, dynamic>;
      }
    } catch (_) {}
    return null;
  }

  static Future<Map<String, dynamic>?> updateOwnerProfile({
    String? nickname,
    String? fullName,
    String? preferredName,
    String? callName,
    String? occupation,
  }) async {
    try {
      final body = <String, dynamic>{};
      if (nickname != null) body['nickname'] = nickname;
      if (fullName != null) body['full_name'] = fullName;
      if (preferredName != null) body['preferred_name'] = preferredName;
      if (callName != null) body['call_name'] = callName;
      if (occupation != null) body['occupation'] = occupation;

      final res = await http.put(
        Uri.parse('$baseUrl/api/v1/memories/profile'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode(body),
      ).timeout(const Duration(seconds: 4));
      if (res.statusCode == 200) {
        return json.decode(res.body) as Map<String, dynamic>;
      }
    } catch (_) {}
    return null;
  }

  // ── 5-Second Voice Recording Controls ────────────────────────────────────

  static Future<String?> startRecording({double duration = 5.0}) async {
    try {
      final res = await http.post(
        Uri.parse('$baseUrl/api/v1/stt/record/start?duration=$duration'),
      ).timeout(const Duration(seconds: 4));
      if (res.statusCode == 200) {
        final data = json.decode(res.body) as Map<String, dynamic>;
        return data['recording_id'] as String?;
      }
    } catch (_) {}
    return null;
  }

  static Future<bool> cancelRecording(String recordingId) async {
    try {
      final res = await http.post(
        Uri.parse('$baseUrl/api/v1/stt/record/cancel?recording_id=$recordingId'),
      ).timeout(const Duration(seconds: 3));
      return res.statusCode == 200;
    } catch (_) {
      return false;
    }
  }

  // ── Agentic Voice Mode ────────────────────────────────────────────────────

  static Future<Map<String, dynamic>?> startAgenticVoice() async {
    try {
      final res = await http.post(Uri.parse('$baseUrl/api/v1/stt/agentic/start')).timeout(const Duration(seconds: 3));
      if (res.statusCode == 200) {
        return json.decode(res.body) as Map<String, dynamic>;
      }
    } catch (_) {}
    return null;
  }

  static Future<Map<String, dynamic>?> stopAgenticVoice() async {
    try {
      final res = await http.post(Uri.parse('$baseUrl/api/v1/stt/agentic/stop')).timeout(const Duration(seconds: 3));
      if (res.statusCode == 200) {
        return json.decode(res.body) as Map<String, dynamic>;
      }
    } catch (_) {}
    return null;
  }

  static Future<Map<String, dynamic>?> pauseAgenticVoice() async {
    try {
      final res = await http.post(Uri.parse('$baseUrl/api/v1/stt/agentic/pause')).timeout(const Duration(seconds: 3));
      if (res.statusCode == 200) {
        return json.decode(res.body) as Map<String, dynamic>;
      }
    } catch (_) {}
    return null;
  }

  static Future<Map<String, dynamic>?> resumeAgenticVoice() async {
    try {
      final res = await http.post(Uri.parse('$baseUrl/api/v1/stt/agentic/resume')).timeout(const Duration(seconds: 3));
      if (res.statusCode == 200) {
        return json.decode(res.body) as Map<String, dynamic>;
      }
    } catch (_) {}
    return null;
  }

  static Future<Map<String, dynamic>?> emergencyStopAgenticVoice() async {
    try {
      final res = await http.post(Uri.parse('$baseUrl/api/v1/stt/agentic/emergency_stop')).timeout(const Duration(seconds: 3));
      if (res.statusCode == 200) {
        return json.decode(res.body) as Map<String, dynamic>;
      }
    } catch (_) {}
    return null;
  }

  static Future<Map<String, dynamic>?> getAgenticVoiceStatus() async {
    try {
      final res = await http.get(Uri.parse('$baseUrl/api/v1/stt/agentic/status')).timeout(const Duration(seconds: 2));
      if (res.statusCode == 200) {
        return json.decode(res.body) as Map<String, dynamic>;
      }
    } catch (_) {}
    return null;
  }

  // ── Persistent Task Reconnection ──────────────────────────────────────────

  static Stream<Map<String, dynamic>> streamTaskEvents(String taskId) async* {
    final client = http.Client();
    try {
      final request = http.Request('GET', Uri.parse('$baseUrl/api/v1/core/task/$taskId/events'));
      final response = await client.send(request);
      final lines = response.stream.toStringStream().transform(const LineSplitter());
      await for (final line in lines) {
        if (line.trim().isEmpty) continue;
        try {
          final data = json.decode(line) as Map<String, dynamic>;
          yield data;
        } catch (_) {}
      }
    } catch (_) {
    } finally {
      client.close();
    }
  }

  static Future<Map<String, dynamic>?> saveSettings(Map<String, dynamic> settings) async {
    try {
      final res = await http.post(
        Uri.parse('$baseUrl/api/v1/settings'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode(settings),
      ).timeout(const Duration(seconds: 4));
      if (res.statusCode == 200) {
        return json.decode(res.body) as Map<String, dynamic>;
      }
    } catch (_) {}
    return null;
  }
}

class ApiClient {
  static Future<Map<String, dynamic>?> getSystemHealth() => EvaApiClient.getDetailedHealth();
  static Future<Map<String, dynamic>?> saveSettings(Map<String, dynamic> settings) => EvaApiClient.saveSettings(settings);
}
