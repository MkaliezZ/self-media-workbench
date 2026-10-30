import {Composition, registerRoot} from 'remotion';
import {ShotFilm, type FilmProps} from './shots';

registerRoot(() => <Composition id="WorkbenchShot" component={ShotFilm}
  width={1920} height={1080} fps={25} durationInFrames={125}
  defaultProps={{} as FilmProps}
  calculateMetadata={({props}) => ({width:props.width, height:props.height,
    fps:props.fps, durationInFrames:props.duration_in_frames})} />);
