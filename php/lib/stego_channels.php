<?php
/**
 * Steganographic Channels
 * Hide canary fragments in innocent-looking content
 */

interface SteganographicChannel {
    public function encode(string $fragment, array $metadata): string;
    public function decode(string $encoded): string;
    public function getChannelType(): string;
}

/**
 * Tire Pressure Forum Channel
 */
class TirePressureChannel implements SteganographicChannel {
    public function encode(string $fragment, array $metadata): string {
        $bytes = array_values(unpack('C*', substr($fragment, 0, 10)));
        
        $year = 2010 + ($bytes[0] % 16);
        $makes = ['Toyota', 'Honda', 'Ford', 'Chevy', 'Nissan'];
        $models = ['Camry', 'Accord', 'F-150', 'Silverado', 'Altima'];
        
        $make = $makes[$bytes[1] % count($makes)];
        $model = $models[$bytes[2] % count($models)];
        
        $frontPSI = 30 + ($bytes[3] % 11);
        $rearPSI = 30 + ($bytes[4] % 11);
        $treadDepth = sprintf("%d/32", 4 + ($bytes[5] % 5));
        
        return <<<TEXT
Looking for tire recommendations for my {$year} {$make} {$model}.
Current pressure: Front {$frontPSI} PSI, Rear {$rearPSI} PSI.
Tread depth: {$treadDepth}.
Planning long road trip. Any advice?
TEXT;
    }
    
    public function decode(string $encoded): string {
        // Extract bytes from PSI values, year, etc.
        preg_match('/(\d{4})\s+(\w+)\s+(\w+)/', $encoded, $vehicle);
        preg_match('/Front\s+(\d+)\s+PSI.*Rear\s+(\d+)\s+PSI/', $encoded, $psi);
        preg_match('/(\d+)\/32/', $encoded, $tread);
        
        $bytes = [
            isset($vehicle[1]) ? (int)$vehicle[1] - 2010 : 0,
            0, // make index (would need reverse lookup)
            0, // model index
            isset($psi[1]) ? (int)$psi[1] - 30 : 0,
            isset($psi[2]) ? (int)$psi[2] - 30 : 0,
            isset($tread[1]) ? (int)$tread[1] - 4 : 0
        ];
        
        return pack('C*', ...$bytes);
    }
    
    public function getChannelType(): string {
        return 'tire_forum';
    }
}

/**
 * FATK Forum Channel (Fishing Reports)
 */
class FATKChannel implements SteganographicChannel {
    public function encode(string $fragment, array $metadata): string {
        $bytes = array_values(unpack('C*', substr($fragment, 0, 10)));
        
        $lakes = ['Lake Michigan', 'Lake Erie', 'Lake Superior', 'Lake Huron'];
        $baits = ['crawfish', 'nightcrawler', 'minnow', 'jig', 'crankbait'];
        
        $location = $lakes[$bytes[0] % count($lakes)];
        $waterTemp = 50 + ($bytes[1] % 21);
        $lineTest = [8, 10, 12, 15, 20][$bytes[2] % 5];
        $bait = $baits[$bytes[3] % count($baits)];
        $catchWeight = 10 + ($bytes[4] % 21);
        $hour = 6 + ($bytes[5] % 7);
        $minute = $bytes[6] % 60;
        $depth = 15 + ($bytes[7] % 31);
        
        $minuteFormatted = sprintf("%02d", $minute);
        return <<<TEXT
Took the boat out to {$location} this weekend.
Water temp was {$waterTemp}°F. Used {$lineTest}lb test line with {$bait} bait.
Caught a {$catchWeight}lb walleye at {$hour}:{$minuteFormatted} AM.
Depth marker showed {$depth} feet. Released after photo.
Great day on the water!
TEXT;
    }
    
    public function decode(string $encoded): string {
        preg_match('/(\d+)°F/', $encoded, $temp);
        preg_match('/(\d+)lb test/', $encoded, $line);
        preg_match('/(\d+)lb walleye/', $encoded, $weight);
        preg_match('/(\d+):(\d+)/', $encoded, $time);
        preg_match('/(\d+) feet/', $encoded, $depth);
        
        $bytes = [
            0, // lake index
            isset($temp[1]) ? (int)$temp[1] - 50 : 0,
            0, // line test index
            0, // bait index
            isset($weight[1]) ? (int)$weight[1] - 10 : 0,
            isset($time[1]) ? (int)$time[1] - 6 : 0,
            isset($time[2]) ? (int)$time[2] : 0,
            isset($depth[1]) ? (int)$depth[1] - 15 : 0
        ];
        
        return pack('C*', ...$bytes);
    }
    
    public function getChannelType(): string {
        return 'fatk_forum';
    }
}

/**
 * Channel Manager
 */
class ChannelManager {
    private array $channels = [];
    
    public function __construct() {
        $this->registerChannel(new TirePressureChannel());
        $this->registerChannel(new FATKChannel());
    }
    
    public function registerChannel(SteganographicChannel $channel): void {
        $this->channels[$channel->getChannelType()] = $channel;
    }
    
    /**
     * Distribute fragment across multiple channels for redundancy.
     */
    public function distributeFragment(string $fragment, array $channelTypes): array {
        $distributions = [];
        
        foreach ($channelTypes as $type) {
            if (!isset($this->channels[$type])) {
                continue;
            }
            
            $channel = $this->channels[$type];
            $encoded = $channel->encode($fragment, []);
            
            $distributions[] = [
                'channel' => $type,
                'cover_content' => $encoded,
                'posted_at' => microtime(true)
            ];
        }
        
        return $distributions;
    }
}
