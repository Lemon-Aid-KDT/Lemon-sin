// devtools/tokens_preview.dart — 디자인 토큰 시각 검증 화면
//
// 사용법:
//   1. main.dart 에서 home: const TokensPreview() 로 일시 교체
//   2. flutter run → 가상폰에서 모든 토큰 한 번에 검증
//   3. 검증 끝나면 main.dart 원복
//
// 다이어리 §4 모든 토큰을 한 화면에 시각화.

import 'package:flutter/material.dart';
import '../utils/tokens.dart';

class TokensPreview extends StatelessWidget {
  const TokensPreview({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Tokens Preview')),
      body: ListView(
        padding: const EdgeInsets.all(LemonSpace.md),
        children: [
          _SectionTitle('1. Color · Brand'),
          _ColorRow('brand', LemonColors.brand, '#4267EC'),
          _ColorRow('brandStrong', LemonColors.brandStrong, '#2945C2'),
          _ColorRow('brandDeep', LemonColors.brandDeep, '#1E2E8E'),
          _ColorRow('brandTint', LemonColors.brandTint, '#DBE4FF'),
          _ColorRow('brandSoft', LemonColors.brandSoft, '#EEF2FF'),

          _SectionTitle('2. Color · Accent (Lemon 캐릭터·컬러 카드)'),
          _ColorRow('citrus', LemonColors.citrus, '#FFD93D'),
          _ColorRow('citrusLight', LemonColors.citrusLight, '#FFF4C2'),
          _ColorRow('pink', LemonColors.pink, '#FFB6C1'),
          _ColorRow('pinkLight', LemonColors.pinkLight, '#FFE6EA'),
          _ColorRow('green', LemonColors.green, '#B8E994'),
          _ColorRow('greenLight', LemonColors.greenLight, '#EAF7DA'),
          _ColorRow('sky', LemonColors.sky, '#A4D8FF'),
          _ColorRow('skyLight', LemonColors.skyLight, '#E1F0FF'),

          _SectionTitle('3. Color · Surface · Text · Line'),
          _ColorRow('bgPage', LemonColors.bgPage, '#F8F9FB'),
          _ColorRow('bgElev', LemonColors.bgElev, '#FFFFFF'),
          _ColorRow('ink', LemonColors.ink, '#1A1F2E'),
          _ColorRow('inkSoft', LemonColors.inkSoft, '#4A5165'),
          _ColorRow('inkMute', LemonColors.inkMute, '#8B92A4'),
          _ColorRow('line', LemonColors.line, '#EEF0F4'),
          _ColorRow('lineStrong', LemonColors.lineStrong, '#C4C9D4'),

          _SectionTitle('4. Color · Semantic'),
          _ColorRow('success', LemonColors.success, '#16A34A'),
          _ColorRow('warning', LemonColors.warning, '#F59E0B'),
          _ColorRow('danger', LemonColors.danger, '#DC2626'),

          _SectionTitle('5. 컬러 카드 시스템 (건강의신 패턴)'),
          _ColorCard('Lemon Card', LemonColors.citrusLight, LemonColors.citrus,
              '참여 · 응모권'),
          _ColorCard('Sky Card', LemonColors.skyLight, LemonColors.sky,
              '정보 · 청구 · 통계'),
          _ColorCard('Pink Card', LemonColors.pinkLight, LemonColors.pink,
              '감정 · 커뮤니티'),
          _ColorCard('Green Card', LemonColors.greenLight, LemonColors.green,
              '식단 · 자연'),
          _ColorCard('Blue Card', LemonColors.brandSoft, LemonColors.brand,
              '메인 액션'),

          _SectionTitle('6. Type Scale'),
          const Text('display 32/800', style: LemonText.display),
          const SizedBox(height: 8),
          const Text('title 24/800', style: LemonText.title),
          const SizedBox(height: 8),
          const Text('heading 20/700', style: LemonText.heading),
          const SizedBox(height: 8),
          const Text('subheading 17/600', style: LemonText.subheading),
          const SizedBox(height: 8),
          const Text('bodyEmphasis 17/700 — 결과 핵심 수치',
              style: LemonText.bodyEmphasis),
          const SizedBox(height: 8),
          const Text('body 16/400 — 일반 본문이 이렇게 보입니다',
              style: LemonText.body),
          const SizedBox(height: 8),
          const Text('caption 13/400 — 도움말 작은 글씨',
              style: LemonText.caption),
          const SizedBox(height: 8),
          const Text('disclaimer 13/400 — 면책 고지', style: LemonText.disclaimer),

          _SectionTitle('7. Type · 고령자 모드 변종'),
          const Text('elder.body 19/400 — 본문이 이렇게 커집니다',
              style: LemonTextElder.body),
          const SizedBox(height: 8),
          const Text('elder.bodyEmphasis 20/700', style: LemonTextElder.bodyEmphasis),
          const SizedBox(height: 8),
          const Text('elder.subheading 20/600', style: LemonTextElder.subheading),
          const SizedBox(height: 8),
          const Text('elder.caption 15/400', style: LemonTextElder.caption),

          _SectionTitle('8. Spacing (4dp 그리드)'),
          _SpaceRow('xs', LemonSpace.xs),
          _SpaceRow('sm', LemonSpace.sm),
          _SpaceRow('md', LemonSpace.md),
          _SpaceRow('lg', LemonSpace.lg),
          _SpaceRow('xl', LemonSpace.xl),
          _SpaceRow('xxl', LemonSpace.xxl),
          _SpaceRow('touchTarget', LemonSpace.touchTarget),
          _SpaceRow('elder.touchTarget', LemonSpaceElder.touchTarget),

          _SectionTitle('9. Radius'),
          _RadiusRow('sm', LemonRadius.sm),
          _RadiusRow('md', LemonRadius.md),
          _RadiusRow('lg', LemonRadius.lg),
          _RadiusRow('xl', LemonRadius.xl),
          _RadiusRow('pill', LemonRadius.pill),

          _SectionTitle('10. Shadow'),
          _ShadowRow('sm', LemonShadow.sm),
          _ShadowRow('md', LemonShadow.md),
          _ShadowRow('lg', LemonShadow.lg),
          _ShadowRow('xl', LemonShadow.xl),

          _SectionTitle('11. Motion (탭해서 확인)'),
          const _MotionDemo(),

          _SectionTitle('12. Button (Theme)'),
          ElevatedButton(
            onPressed: () {},
            child: const Text('Primary Button'),
          ),
          const SizedBox(height: 8),
          OutlinedButton(
            onPressed: () {},
            child: const Text('Secondary Button'),
          ),
          const SizedBox(height: 8),
          TextButton(
            onPressed: () {},
            child: const Text('Ghost Button'),
          ),

          _SectionTitle('13. Input · Chip'),
          const TextField(
            decoration: InputDecoration(
              labelText: '이메일',
              hintText: 'name@email.com',
            ),
          ),
          const SizedBox(height: LemonSpace.md),
          Wrap(
            spacing: LemonSpace.sm,
            children: const [
              Chip(label: Text('영양제')),
              Chip(label: Text('식단')),
              Chip(label: Text('검진지')),
              Chip(label: Text('체중')),
            ],
          ),

          _SectionTitle('14. Card · Snackbar · Dialog'),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(LemonSpace.md),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: const [
                  Text('Card.theme', style: LemonText.subheading),
                  SizedBox(height: 4),
                  Text('카드 기본 스타일', style: LemonText.body),
                ],
              ),
            ),
          ),
          const SizedBox(height: LemonSpace.md),
          Row(
            children: [
              Expanded(
                child: OutlinedButton(
                  onPressed: () {
                    ScaffoldMessenger.of(context).showSnackBar(
                      SnackBar(
                        content: const Text('Snackbar 토큰 확인'),
                        action: SnackBarAction(
                          label: '닫기',
                          onPressed: () {},
                        ),
                      ),
                    );
                  },
                  child: const Text('Snackbar'),
                ),
              ),
              const SizedBox(width: LemonSpace.sm),
              Expanded(
                child: OutlinedButton(
                  onPressed: () {
                    showDialog<void>(
                      context: context,
                      builder: (_) => AlertDialog(
                        title: const Text('Dialog'),
                        content: const Text('다이얼로그 토큰 확인'),
                        actions: [
                          TextButton(
                            onPressed: () => Navigator.pop(context),
                            child: const Text('확인'),
                          ),
                        ],
                      ),
                    );
                  },
                  child: const Text('Dialog'),
                ),
              ),
            ],
          ),

          const SizedBox(height: LemonSpace.xxl),
        ],
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: () {},
        child: const Icon(Icons.camera_alt),
      ),
      bottomNavigationBar: BottomNavigationBar(
        items: const [
          BottomNavigationBarItem(icon: Icon(Icons.home), label: '홈'),
          BottomNavigationBarItem(icon: Icon(Icons.favorite), label: '건강'),
          BottomNavigationBarItem(icon: Icon(Icons.chat_bubble), label: '챗봇'),
          BottomNavigationBarItem(icon: Icon(Icons.card_giftcard), label: '응모권'),
          BottomNavigationBarItem(icon: Icon(Icons.settings), label: '설정'),
        ],
      ),
    );
  }
}

// ─── 헬퍼 위젯들 ───

class _SectionTitle extends StatelessWidget {
  final String text;
  const _SectionTitle(this.text);

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(
        top: LemonSpace.xl,
        bottom: LemonSpace.md,
      ),
      child: Text(text, style: LemonText.heading),
    );
  }
}

class _ColorRow extends StatelessWidget {
  final String name;
  final Color color;
  final String hex;

  const _ColorRow(this.name, this.color, this.hex);

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        children: [
          Container(
            width: 56,
            height: 32,
            decoration: BoxDecoration(
              color: color,
              borderRadius: BorderRadius.circular(LemonRadius.sm),
              border: Border.all(color: LemonColors.line),
            ),
          ),
          const SizedBox(width: LemonSpace.md),
          Expanded(child: Text(name, style: LemonText.body)),
          Text(hex, style: LemonText.caption),
        ],
      ),
    );
  }
}

class _ColorCard extends StatelessWidget {
  final String name;
  final Color bg;
  final Color accent;
  final String purpose;

  const _ColorCard(this.name, this.bg, this.accent, this.purpose);

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Container(
        padding: const EdgeInsets.all(LemonSpace.md),
        decoration: BoxDecoration(
          color: bg,
          borderRadius: BorderRadius.circular(LemonRadius.lg),
        ),
        child: Row(
          children: [
            Container(
              width: 8,
              height: 40,
              decoration: BoxDecoration(
                color: accent,
                borderRadius: BorderRadius.circular(LemonRadius.sm),
              ),
            ),
            const SizedBox(width: LemonSpace.md),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(name, style: LemonText.subheading),
                  Text(purpose, style: LemonText.caption),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _SpaceRow extends StatelessWidget {
  final String name;
  final double value;

  const _SpaceRow(this.name, this.value);

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        children: [
          SizedBox(
            width: 140,
            child: Text('$name (${value.toInt()}dp)', style: LemonText.body),
          ),
          Container(
            width: value,
            height: 16,
            color: LemonColors.brand,
          ),
        ],
      ),
    );
  }
}

class _RadiusRow extends StatelessWidget {
  final String name;
  final double value;

  const _RadiusRow(this.name, this.value);

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        children: [
          SizedBox(
            width: 100,
            child: Text('$name (${value.toInt()})', style: LemonText.body),
          ),
          Container(
            width: 80,
            height: 40,
            decoration: BoxDecoration(
              color: LemonColors.brandSoft,
              borderRadius: BorderRadius.circular(value),
              border: Border.all(color: LemonColors.brand),
            ),
          ),
        ],
      ),
    );
  }
}

class _ShadowRow extends StatelessWidget {
  final String name;
  final List<BoxShadow> shadow;

  const _ShadowRow(this.name, this.shadow);

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: LemonSpace.sm),
      child: Row(
        children: [
          SizedBox(width: 100, child: Text(name, style: LemonText.body)),
          Container(
            width: 100,
            height: 60,
            decoration: BoxDecoration(
              color: LemonColors.bgElev,
              borderRadius: BorderRadius.circular(LemonRadius.lg),
              boxShadow: shadow,
            ),
          ),
        ],
      ),
    );
  }
}

class _MotionDemo extends StatefulWidget {
  const _MotionDemo();

  @override
  State<_MotionDemo> createState() => _MotionDemoState();
}

class _MotionDemoState extends State<_MotionDemo> {
  Duration _duration = LemonMotion.base;
  String _label = 'base 200ms';
  bool _toggled = false;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Wrap(
          spacing: LemonSpace.sm,
          children: [
            _btn('fast 80', LemonMotion.fast),
            _btn('base 200', LemonMotion.base),
            _btn('slow 320', LemonMotion.slow),
            _btn('entry 400', LemonMotion.entry),
            _btn('exit 160', LemonMotion.exit),
          ],
        ),
        const SizedBox(height: LemonSpace.md),
        Text('현재: $_label · 박스 탭해보기', style: LemonText.caption),
        const SizedBox(height: LemonSpace.sm),
        GestureDetector(
          onTap: () => setState(() => _toggled = !_toggled),
          child: AnimatedContainer(
            duration: _duration,
            curve: LemonMotion.curveDefault,
            width: _toggled ? 240 : 80,
            height: 60,
            decoration: BoxDecoration(
              color: _toggled ? LemonColors.brand : LemonColors.brandSoft,
              borderRadius: BorderRadius.circular(LemonRadius.lg),
            ),
            alignment: Alignment.center,
            child: Text(
              _toggled ? '여기까지' : '탭',
              style: LemonText.body.copyWith(
                color: _toggled ? Colors.white : LemonColors.brand,
              ),
            ),
          ),
        ),
      ],
    );
  }

  Widget _btn(String label, Duration d) {
    return ChoiceChip(
      label: Text(label),
      selected: _label.startsWith(label.split(' ').first),
      onSelected: (_) => setState(() {
        _duration = d;
        _label = label;
      }),
    );
  }
}
